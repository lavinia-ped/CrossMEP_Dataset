#!/usr/bin/env python3
"""Catalog stress test (paper section 5.3): error bars, sensitivity and demand.

The paper asks how much of the benchmark a small clamp catalog can attach.  This
script answers it as a measurement rather than a single number.  Definitions
(what "attachable" means) are in ``crossmep/catalog.py``.

What is computed
----------------
1. **Coverage with error bars.**  Share of pipes the catalog can attach on the
   released benchmark, with a 95 % cluster-bootstrap interval (contexts are
   resampled as units, because the elements of one context are correlated:
   banks of pipes share a size); overall and per tier; the same on every
   released split; and the reasons for every miss (not a pipe / no size fits /
   too heavy).
2. **Population estimate.**  Per-tier coverage from a large Monte Carlo sample of
   the generator itself (the data-generating process), with its own interval.
   This separates sampling noise in the 125-context tiers of the benchmark from
   real differences between tiers.
3. **Which sizes are attached.**  Pipes and attachable pipes per nominal size.
4. **Sensitivity.**  The result under the three attach-diameter rules and under
   bin-edge tolerances of 0, 0.5 and 1 mm.
5. **Catalog-independent demand curve.**  The largest share of pipes that k clamp
   sizes, each fitting a diameter window of at most ``--width`` mm, could attach
   (exact optimum), i.e. what the dataset asks of ANY catalog.

Everything is deterministic: bootstrap and Monte Carlo seeds are arguments.
Only NumPy is required.

Usage::

    python verify/catalog_stress.py                 # the paper's catalog, default settings
    python verify/catalog_stress.py --json          # machine-readable
    python verify/catalog_stress.py --bins 40:60:2.0,100:120:3.0   # your catalog
    python verify/catalog_stress.py --mc-per-tier 0                # skip the Monte Carlo step
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import crossmep.catalog as cat  # noqa: E402
import crossmep.tasks as cm  # noqa: E402
from crossmep.io import RELEASE_SPLITS  # noqa: E402

TIERS = [f"C{n}" for n in range(1, 9)]
TOLERANCES_MM = (0.0, 0.5, 1.0)
WIDTHS_MM = (0.0, 6.0, 12.0, 24.0, 48.0)          # clamp-size windows tried in the demand sensitivity
SIZES_SHOWN = (1, 2, 3, 4, 6)                      # catalog sizes k shown in the demand sensitivity


# --------------------------------------------------------------------------- statistics

def context_counts(contexts: Sequence[dict], bins, rule: str, tol_mm: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-context (pipes, attachable pipes) and the tier of each context."""
    n_pipes = np.zeros(len(contexts))
    n_cov = np.zeros(len(contexts))
    for i, c in enumerate(contexts):
        for e in c["elements"]:
            r = cat.classify(e, bins, rule, tol_mm)
            if r != "not_pipe":
                n_pipes[i] += 1
                n_cov[i] += r == "covered"
    return n_pipes, n_cov, np.array([c["tier"] for c in contexts])


def cluster_interval(n_pipes: np.ndarray, n_cov: np.ndarray, n_boot: int, rng: np.random.Generator,
                     level: float = 0.95) -> Dict[str, float]:
    """Percentile cluster-bootstrap interval of (attachable pipes / pipes), in percent.

    A resample that happens to contain no pipe has no defined share and is left
    out; with no pipes at all the result is NaN.  (Only matters for very small samples.)
    """
    n = len(n_pipes)
    if n_pipes.sum() == 0:
        return {"pct": float("nan"), "lo": float("nan"), "hi": float("nan")}
    est = n_cov.sum() / n_pipes.sum()
    stats = np.empty(n_boot)
    chunk = max(1, 4_000_000 // n)
    with np.errstate(invalid="ignore", divide="ignore"):
        for s in range(0, n_boot, chunk):
            m = min(chunk, n_boot - s)
            idx = rng.integers(0, n, size=(m, n))
            stats[s:s + m] = n_cov[idx].sum(axis=1) / n_pipes[idx].sum(axis=1)
    stats = stats[np.isfinite(stats)]
    a = 100.0 * (1.0 - level) / 2.0
    lo, hi = np.percentile(stats, [a, 100.0 - a])
    return {"pct": 100.0 * float(est), "lo": 100.0 * float(lo), "hi": 100.0 * float(hi)}


def intervals(contexts: Sequence[dict], bins, rule: str, tol_mm: float, n_boot: int, seed: int) -> Dict:
    """Overall and per-tier coverage with cluster-bootstrap intervals."""
    rng = np.random.default_rng(seed)
    n_pipes, n_cov, tiers = context_counts(contexts, bins, rule, tol_mm)
    out = {"overall": cluster_interval(n_pipes, n_cov, n_boot, rng), "per_tier": {}}
    for t in TIERS:
        m = tiers == t
        if m.any() and n_pipes[m].sum() > 0:
            out["per_tier"][t] = cluster_interval(n_pipes[m], n_cov[m], n_boot, rng)
    return out


def population_estimate(bins, rule: str, tol_mm: float, per_tier: int, n_boot: int, seed: int) -> Dict:
    """Coverage per tier from ``per_tier`` freshly generated contexts of every tier."""
    from crossmep.generate import generate_dataset
    rng = np.random.default_rng(seed)
    parts = []
    out: Dict = {"contexts_per_tier": per_tier, "seed": seed, "per_tier": {}}
    for i, t in enumerate(TIERS):
        ctxs = [c.to_dict() for c in generate_dataset(per_tier, seed=seed + i, tier=t)]
        n_pipes, n_cov, _ = context_counts(ctxs, bins, rule, tol_mm)
        parts.append((n_pipes, n_cov))
        out["per_tier"][t] = cluster_interval(n_pipes, n_cov, n_boot, rng)
    out["overall"] = cluster_interval(np.concatenate([p for p, _ in parts]), np.concatenate([c for _, c in parts]),
                                      n_boot, rng)
    return out


# --------------------------------------------------------------------------- the report

def stress_test(bins, rule: str = "service", tol_mm: float = 0.0, n_boot: int = 2000, seed: int = 0,
                mc_per_tier: int = 2000, mc_seed: int = 7, width_mm: float = 6.0,
                splits: Dict[str, List[dict]] = None) -> Dict:
    bins = cat.as_bins(bins)
    splits = splits or {s: cm.load(s) for s in RELEASE_SPLITS}
    bench = splits["benchmark"]
    pooled = [c for s in RELEASE_SPLITS if s in splits for c in splits[s]]
    rep: Dict = {"settings": {"bins": [list(b) for b in bins], "rule": rule, "tol_mm": tol_mm, "n_boot": n_boot,
                              "seed": seed, "mc_per_tier": mc_per_tier, "mc_seed": mc_seed, "width_mm": width_mm}}

    # 1. benchmark: counts, outcome decomposition, intervals
    s = cat.summary(bench, bins, rule, tol_mm)
    ci = intervals(bench, bins, rule, tol_mm, n_boot, seed)
    rep["benchmark"] = {k: s[k] for k in ("elements", "pipes", "covered", "size", "load", "not_pipe")}
    rep["benchmark"]["pct_pipes"] = ci["overall"]["pct"]
    rep["benchmark"]["ci"] = [ci["overall"]["lo"], ci["overall"]["hi"]]
    rep["benchmark"]["pct_all_elements"] = 100.0 * s["covered"] / s["elements"]
    rep["benchmark"]["per_tier"] = {t: {"pipes": s["per_tier"][t]["pipes"], "covered": s["per_tier"][t]["covered"],
                                        **ci["per_tier"][t]} for t in ci["per_tier"]}
    pipes = [e["load_kN"] for c in bench for e in c["elements"] if e["kind"] == "pipe"]
    rep["benchmark"]["max_pipe_load_kN"] = max(pipes)
    rep["benchmark"]["min_bin_capacity_kN"] = min(b.capacity_kN for b in bins)

    # 1b. every released split
    rep["splits"] = {}
    for name in RELEASE_SPLITS:
        if name in splits:
            c = intervals(splits[name], bins, rule, tol_mm, n_boot, seed)["overall"]
            ss = cat.summary(splits[name], bins, rule, tol_mm)
            rep["splits"][name] = {"pipes": ss["pipes"], "pct": c["pct"], "ci": [c["lo"], c["hi"]]}

    # 2. population estimate
    if mc_per_tier > 0:
        rep["population"] = population_estimate(bins, rule, tol_mm, mc_per_tier, n_boot, mc_seed)

    # 3. which sizes are attached (benchmark and all splits)
    for key, data in (("by_size", bench), ("by_size_all_splits", pooled)):
        sizes: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
        for c in data:
            for e in c["elements"]:
                if e["kind"] == "pipe":
                    r = cat.classify(e, bins, rule, tol_mm)
                    sizes[e["label"]][0] += 1
                    sizes[e["label"]][1] += r == "covered"
        rep[key] = {k: {"pipes": v[0], "covered": v[1]} for k, v in sorted(sizes.items(), key=lambda kv: float(kv[0][2:]))}

    # 4. sensitivity of the headline number
    rep["sensitivity"] = [{"rule": r, "tol_mm": t, "pct_benchmark": cat.summary(bench, bins, r, t)["pct_pipes"],
                           "pct_all_splits": cat.summary(pooled, bins, r, t)["pct_pipes"]}
                          for r in cat.DIAMETER_RULES for t in TOLERANCES_MM]

    # 5. demand curve, independent of any catalog
    points = cat.demand_points(bench, rule)
    curve = cat.demand_curve(points, width_mm)
    rep["demand"] = {"width_mm": width_mm, "pipes": sum(points.values()), "distinct_diameters": len(points),
                     "curve": [{"k": r["k"], "pct": r["pct"], "windows": [list(w) for w in r["windows"]]} for r in curve],
                     "diameters": {str(d): n for d, n in sorted(points.items())}}
    points_all = cat.demand_points(pooled, rule)
    rep["demand"]["curve_all_splits"] = [{"k": r["k"], "pct": r["pct"]} for r in cat.demand_curve(points_all, width_mm)]
    total = sum(points.values())
    rep["demand"]["by_width"] = {format(w, "g"): {str(k): 100.0 * cat.best_windows(points, k, w)[0] / total
                                                 for k in SIZES_SHOWN} for w in WIDTHS_MM}
    return rep


def render(r: Dict) -> str:
    L: List[str] = []
    st, b = r["settings"], r["benchmark"]
    L.append("Catalog: " + ", ".join(f"{lo:g}-{hi:g} mm up to {cap:g} kN" for lo, hi, cap in st["bins"])
             + f"   (attach diameter rule '{st['rule']}', tolerance {st['tol_mm']:g} mm)")
    L.append(f"Benchmark: {b['pipes']:,} pipes, {b['elements']:,} elements")
    L.append(f"  attachable pipes   {b['covered']:>6,}  = {b['pct_pipes']:.1f} % of pipes "
             f"(95 % CI {b['ci'][0]:.1f}-{b['ci'][1]:.1f}), {b['pct_all_elements']:.1f} % of all elements")
    L.append(f"  missed: no size fits {b['size']:,} pipes; too heavy {b['load']:,} pipes; not a pipe {b['not_pipe']:,} elements")
    L.append(f"  heaviest pipe {b['max_pipe_load_kN']:.2f} kN vs weakest bin {b['min_bin_capacity_kN']:g} kN"
             f" -> load {'never' if b['load'] == 0 else 'sometimes'} binds")
    L.append("")
    L.append(f"{'tier':<6}{'pipes':>7}{'attach':>8}{'% (95 % CI)':>20}" + ("" if "population" not in r else f"{'population % (95 % CI)':>28}"))
    for t, v in b["per_tier"].items():
        line = f"{t:<6}{v['pipes']:>7}{v['covered']:>8}{v['pct']:>10.1f} ({v['lo']:.1f}-{v['hi']:.1f})"
        if "population" in r and t in r["population"]["per_tier"]:
            p = r["population"]["per_tier"][t]
            line += f"{p['pct']:>16.1f} ({p['lo']:.1f}-{p['hi']:.1f})"
        L.append(line)
    if "population" in r:
        p = r["population"]
        L.append(f"population ({p['contexts_per_tier']:,} contexts per tier, seed {p['seed']}): "
                 f"{p['overall']['pct']:.1f} % (95 % CI {p['overall']['lo']:.1f}-{p['overall']['hi']:.1f})")
    L.append("splits: " + "; ".join(f"{n} {v['pct']:.1f} % ({v['ci'][0]:.1f}-{v['ci'][1]:.1f}, {v['pipes']:,} pipes)"
                                   for n, v in r["splits"].items()))
    L.append("")
    L.append("Attachable pipes by nominal size (benchmark):  " + "  ".join(
        f"{k} {v['covered']}/{v['pipes']}" for k, v in r["by_size"].items()))
    L.append("")
    L.append(f"{'attach diameter rule':<22}" + "".join(f"{'tol ' + format(t, 'g') + ' mm':>14}" for t in TOLERANCES_MM) + "   (% of benchmark pipes; all splits in brackets)")
    for rule in cat.DIAMETER_RULES:
        rows = [x for x in r["sensitivity"] if x["rule"] == rule]
        L.append(f"{rule:<22}" + "".join(f"{x['pct_benchmark']:>7.1f} ({x['pct_all_splits']:>4.1f})" for x in rows))
    L.append("")
    d = r["demand"]
    L.append(f"Demand: best coverage with k clamp sizes, each fitting a window of at most {d['width_mm']:g} mm "
             f"({d['pipes']:,} benchmark pipes, {d['distinct_diameters']} distinct attach diameters)")
    for x in d["curve"]:
        L.append(f"  k = {x['k']:>2}: {x['pct']:5.1f} %   " + "  ".join(f"{lo:g}-{hi:g}" for lo, hi in x["windows"]))
    L.append("")
    L.append("Best coverage (%) by clamp-size window width and number of sizes k:")
    L.append(f"{'window width':<16}" + "".join(f"{'k = ' + str(k):>9}" for k in SIZES_SHOWN))
    for w, row in d["by_width"].items():
        L.append(f"{w + ' mm':<16}" + "".join(f"{row[str(k)]:>9.1f}" for k in SIZES_SHOWN))
    return "\n".join(L)


def parse_bins(text: str):
    return cat.as_bins(tuple(float(x) for x in part.split(":")) for part in text.split(","))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bins", type=parse_bins, default=cat.PAPER_CATALOG,
                    help="lo:hi:capacity_kN[,lo:hi:capacity_kN...] (default: the paper's two-size catalog)")
    ap.add_argument("--rule", choices=cat.DIAMETER_RULES, default="service")
    ap.add_argument("--tol", type=float, default=0.0, help="bin-edge tolerance, mm")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mc-per-tier", type=int, default=2000, help="Monte Carlo contexts per tier (0 = skip)")
    ap.add_argument("--mc-seed", type=int, default=7)
    ap.add_argument("--width", type=float, default=6.0, help="diameter window of one clamp size for the demand curve, mm")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = stress_test(a.bins, a.rule, a.tol, a.n_boot, a.seed, a.mc_per_tier, a.mc_seed, a.width)
    print(json.dumps(r, indent=1) if a.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Experiment 1 (paper section 5.1) with error bars: do congestion and load rise with the tier?

Element count is exact by construction, so the tiers are checked on what is
not: the minimum clear gap between insulation surfaces (congestion), the total
load at the support and the bundle width.  For each, per tier:

* the benchmark median with a 95 % bootstrap interval (125 contexts per tier);
* the population median from a large Monte Carlo sample of the generator (the
  data-generating process), with its own interval;
* the step between neighbouring tiers with an interval, which says whether a
  swap of neighbouring benchmark medians is a real reversal or sampling noise;
* Spearman's rank correlation between tier and metric, with an interval.

Deterministic (seeds are arguments).  NumPy only.

Usage::

    python verify/tier_trends.py                      # benchmark + 2,000 generated contexts per tier
    python verify/tier_trends.py --per-tier 500       # faster
    python verify/tier_trends.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Sequence

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import crossmep.tasks as cm  # noqa: E402

TIERS = [f"C{n}" for n in range(1, 9)]
METRICS = {"clear_gap_mm": "minimum clear gap (mm)", "load_kN": "total load (kN)", "bundle_width_mm": "bundle width (mm)"}


def metric_values(contexts: Sequence[Dict]) -> Dict[str, Dict[str, np.ndarray]]:
    """{metric: {tier: values}}; the clear gap is undefined for one-element contexts."""
    out: Dict[str, Dict[str, List[float]]] = {m: {t: [] for t in TIERS} for m in METRICS}
    for c in contexts:
        t = c["tier"]
        g = cm.min_clear_gap(c)
        if g is not None:
            out["clear_gap_mm"][t].append(g)
        out["load_kN"][t].append(c["total_load_kN"])
        out["bundle_width_mm"][t].append(c["bundle_width_mm"])
    return {m: {t: np.array(v, float) for t, v in d.items() if v} for m, d in out.items()}


def boot_medians(x: np.ndarray, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    return np.median(x[idx], axis=1)


def _ci(v: np.ndarray, level: float = 0.95):
    a = 100 * (1 - level) / 2
    lo, hi = np.percentile(v, [a, 100 - a])
    return float(lo), float(hi)


def _ranks(x: np.ndarray) -> np.ndarray:
    """Average ranks (ties share their mean rank)."""
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[order] = np.arange(1, len(x) + 1)
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=r)
    return (sums / counts)[inv]


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = _ranks(x), _ranks(y)
    rx, ry = rx - rx.mean(), ry - ry.mean()
    return float(np.sum(rx * ry) / np.sqrt(np.sum(rx ** 2) * np.sum(ry ** 2)))


def trends(vals: Dict[str, Dict[str, np.ndarray]], n_boot: int, seed: int) -> Dict:
    rng = np.random.default_rng(seed)
    out: Dict = {}
    for m, by_tier in vals.items():
        tiers = [t for t in TIERS if t in by_tier]
        boots = {t: boot_medians(by_tier[t], n_boot, rng) for t in tiers}
        per_tier = {t: {"n": int(len(by_tier[t])), "median": float(np.median(by_tier[t])), "ci": _ci(boots[t])} for t in tiers}
        steps = {}
        for a, b in zip(tiers, tiers[1:]):
            d = boots[b] - boots[a]
            steps[f"{a}->{b}"] = {"diff": per_tier[b]["median"] - per_tier[a]["median"], "ci": _ci(d)}
        x = np.concatenate([np.full(len(by_tier[t]), int(t[1:])) for t in tiers])
        y = np.concatenate([by_tier[t] for t in tiers])
        rho_b = []
        n = len(x)
        for _ in range(min(n_boot, 500)):
            i = rng.integers(0, n, n)
            rho_b.append(spearman(x[i], y[i]))
        medians = [per_tier[t]["median"] for t in tiers]
        out[m] = {"per_tier": per_tier, "steps": steps, "spearman": spearman(x, y), "spearman_ci": _ci(np.array(rho_b)),
                  "monotone_medians": bool(all(np.diff(medians) < 0)) if m == "clear_gap_mm" else bool(all(np.diff(medians) > 0))}
    return out


def population(per_tier: int, seed: int) -> List[Dict]:
    from crossmep.generate import generate_dataset
    ctxs: List[Dict] = []
    for i, t in enumerate(TIERS):
        ctxs += [c.to_dict() for c in generate_dataset(per_tier, seed=seed + i, tier=t)]
    return ctxs


def run(benchmark: Sequence[Dict], per_tier: int = 2000, n_boot: int = 2000, seed: int = 0, mc_seed: int = 11) -> Dict:
    rep = {"settings": {"per_tier": per_tier, "n_boot": n_boot, "seed": seed, "mc_seed": mc_seed},
           "benchmark": trends(metric_values(benchmark), n_boot, seed)}
    if per_tier > 0:
        rep["population"] = trends(metric_values(population(per_tier, mc_seed)), n_boot, seed)
    return rep


def render(r: Dict) -> str:
    L: List[str] = []
    pop = r.get("population")
    for m, label in METRICS.items():
        b = r["benchmark"][m]
        L.append(f"{label}: Spearman rho with tier {b['spearman']:+.2f} ({b['spearman_ci'][0]:+.2f} to {b['spearman_ci'][1]:+.2f})"
                 + (f"; population {pop[m]['spearman']:+.2f}" if pop else ""))
        L.append(f"  {'tier':<5}{'benchmark median (95 % CI)':>30}" + (f"{'population median (95 % CI)':>32}" if pop else "")
                 + f"{'benchmark step (95 % CI)':>30}")
        prev = None
        for t, v in b["per_tier"].items():
            fmt = "{:.2f}" if m == "load_kN" else "{:.0f}"
            cell = f"{fmt.format(v['median'])} ({fmt.format(v['ci'][0])}-{fmt.format(v['ci'][1])})"
            line = f"  {t:<5}{cell:>30}"
            if pop:
                p = pop[m]["per_tier"][t]
                line += f"{fmt.format(p['median']) + ' (' + fmt.format(p['ci'][0]) + '-' + fmt.format(p['ci'][1]) + ')':>32}"
            if prev:
                s = b["steps"][f"{prev}->{t}"]
                sig = "" if s["ci"][0] <= 0 <= s["ci"][1] else "  *"
                line += f"{fmt.format(s['diff']) + ' (' + fmt.format(s['ci'][0]) + ' to ' + fmt.format(s['ci'][1]) + ')' + sig:>30}"
            L.append(line)
            prev = t
        L.append(f"  medians monotone: benchmark {b['monotone_medians']}" + (f", population {pop[m]['monotone_medians']}" if pop else ""))
        L.append("")
    if pop:
        L.append(f"population: {r['settings']['per_tier']:,} generated contexts per tier (seed {r['settings']['mc_seed']}+i); "
                 "* = the step's interval excludes zero")
    return "\n".join(L).rstrip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-tier", type=int, default=2000, help="generated contexts per tier (0 = skip)")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mc-seed", type=int, default=11)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = run(cm.load("benchmark"), a.per_tier, a.n_boot, a.seed, a.mc_seed)
    print(json.dumps(r, indent=1) if a.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())

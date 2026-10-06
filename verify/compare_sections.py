#!/usr/bin/env python3
"""Generated vs measured pipe gaps on sections of two open buildings, with uncertainty.

The realism check of the clear-gap distribution (paper section 5.2), redone on
measurements that match what a CrossMEP context is -- a section at a support --
and on a second, held-out building.

Measured side (``verify/measured/*.json``, written by ``measure_ifc.py``): sections
cut every 250 mm through the buildingSMART Duplex Apartment (MEP and Plumbing
models) and Medical-Dental Clinic (Plumbing model; a real building, redacted),
CC BY 4.0.  One row per pair of side-by-side pipes, with its gap between bare
surfaces and the number of sections it appears in.

Generated side: gaps between along-adjacent pipes in the same row of each context
(bare surfaces: the quantity a model of flow segments records), released
benchmark split by default.

What is computed (gaps < 600 mm, the range used throughout the paper)
----------------------------------------------------------------------
* Wasserstein-1 distance (mm) between the generated and each measured
  distribution.  Primary: measured pairs weighted by their number of sections,
  i.e. the gap distribution met at a random support location along the runs.
  Sensitivity: every measured pair counted once.
* 95 % percentile bootstrap intervals: generated gaps resampled by context,
  measured gaps by pair (the units that are independent).
* Noise floor: the distance a perfect generator would still show at the measured
  sample size (W1 between the generated distribution and samples of the same size
  and weights drawn from it): median and 95th percentile.
* Real-to-real distances between the measured models, with intervals: how far
  real models are from each other.
* Baseline: a fixed 25 mm gap (the published minimum).
* ``--sensitivity``: the same distances with the section-cut parameters changed one
  at a time, re-measured from the shipped segment tables (no IfcOpenShell needed).

The duct model of the clinic (HVAC) is summarised but not compared: the benchmark
has only 13 duct-duct neighbour pairs.

Usage::

    python verify/compare_sections.py                 # released benchmark, revision 4.0
    python verify/compare_sections.py --json
    python verify/compare_sections.py --n-boot 200    # faster
    python verify/compare_sections.py --sensitivity   # re-measure under other cut parameters
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import crossmep.tasks as cm  # noqa: E402
from crossmep.io import DATA_VERSION, read_payload, split_path  # noqa: E402

MEASURED_DIR = os.path.join(HERE, "measured")
SEGMENTS_DIR = os.path.join(MEASURED_DIR, "segments")
VARIATIONS = (("as measured", {}), ("sections every 125 mm", {"step_mm": 125.0}), ("sections every 500 mm", {"step_mm": 500.0}),
              ("row band 200 mm", {"band_mm": 200.0}), ("row band 800 mm", {"band_mm": 800.0}),
              ("bundle break 600 mm", {"break_mm": 600.0}), ("bundle break 2,400 mm", {"break_mm": 2400.0}),
              ("axis tolerance 1 deg", {"angle_tol_deg": 1.0}), ("axis tolerance 5 deg", {"angle_tol_deg": 5.0}),
              ("min. run length 100 mm", {"min_length_mm": 100.0}), ("min. run length 500 mm", {"min_length_mm": 500.0}))
PIPE_MODELS = (("clinic_plumbing", "Clinic, Plumbing model"),
               ("duplex_mep", "Duplex, MEP model"),
               ("duplex_plumbing", "Duplex, Plumbing model"))
DUCT_MODELS = (("clinic_hvac", "Clinic, HVAC model"),)
RANGE_MAX_MM = 600.0
FIXED_GAP_MM = 25.0


# --------------------------------------------------------------------------- samples

def load_measured(name: str) -> Dict:
    with open(os.path.join(MEASURED_DIR, name + ".json")) as f:
        return json.load(f)


def measured_sample(rec: Dict, kinds: Sequence[str] = ("pipe", "pipe"),
                    range_max_mm: float = RANGE_MAX_MM) -> Tuple[np.ndarray, np.ndarray]:
    """(gaps, section counts) of the measured pairs of the given kinds below the range limit."""
    rows = [p for p in rec["pairs"] if p["kinds"] == sorted(kinds) and p["gap_mm"] < range_max_mm]
    return (np.array([p["gap_mm"] for p in rows], float), np.array([p["n_sections"] for p in rows], float))


def generated_samples(contexts: Sequence[Dict], kinds: Sequence[str] = ("pipe", "pipe"),
                      range_max_mm: float = RANGE_MAX_MM) -> List[np.ndarray]:
    """Per context: bare-surface gaps between along-adjacent neighbours of the given kinds."""
    want = sorted(kinds)
    out: List[np.ndarray] = []
    for c in contexts:
        sk = c["surface"]["kind"]
        g: List[float] = []
        for lvl in sorted({e["level"] for e in c["elements"]}):
            row = sorted((e for e in c["elements"] if e["level"] == lvl), key=lambda e: e["along_mm"])
            for a, b in zip(row, row[1:]):
                if sorted((a["kind"], b["kind"])) == want:
                    gap = (b["along_mm"] - a["along_mm"]) - (cm._along(a, sk) + cm._along(b, sk)) / 2.0
                    if gap < range_max_mm:
                        g.append(gap)
        out.append(np.array(g, float))
    return out


# --------------------------------------------------------------------------- statistics

def w1(a: Sequence[float], b: Sequence[float], wa: Optional[Sequence[float]] = None,
       wb: Optional[Sequence[float]] = None) -> float:
    """Exact Wasserstein-1 distance between two weighted empirical distributions."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    wa = np.ones(len(a)) if wa is None else np.asarray(wa, float)
    wb = np.ones(len(b)) if wb is None else np.asarray(wb, float)
    xs = np.concatenate([a, b])
    order = np.argsort(xs, kind="mergesort")
    da = np.concatenate([wa / wa.sum(), np.zeros(len(b))])[order]
    db = np.concatenate([np.zeros(len(a)), wb / wb.sum()])[order]
    xs = xs[order]
    return float(np.sum(np.abs(np.cumsum(da) - np.cumsum(db))[:-1] * np.diff(xs)))


def _ci(values: np.ndarray, level: float = 0.95) -> Tuple[float, float]:
    a = 100.0 * (1.0 - level) / 2.0
    lo, hi = np.percentile(values, [a, 100.0 - a])
    return float(lo), float(hi)


def weighted_quantile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    o = np.argsort(x, kind="mergesort")
    cw = np.cumsum(w[o]) / w.sum()
    return float(x[o][min(np.searchsorted(cw, q), len(x) - 1)])


def gen_to_real(gen_ctx: List[np.ndarray], gaps: np.ndarray, weights: np.ndarray, n_boot: int,
                rng: np.random.Generator, weighted: bool) -> Dict[str, float]:
    gen = np.concatenate(gen_ctx)
    w = weights if weighted else None
    est = w1(gen, gaps, None, w)
    stats = np.empty(n_boot)
    nc, nm = len(gen_ctx), len(gaps)
    for i in range(n_boot):
        g = np.concatenate([gen_ctx[j] for j in rng.integers(0, nc, nc)])
        k = rng.integers(0, nm, nm)
        stats[i] = w1(g, gaps[k], None, None if w is None else w[k])
    lo, hi = _ci(stats)
    return {"w1": est, "lo": lo, "hi": hi}


def real_to_real(x: Tuple[np.ndarray, np.ndarray], y: Tuple[np.ndarray, np.ndarray], n_boot: int,
                 rng: np.random.Generator, weighted: bool) -> Dict[str, float]:
    (gx, wx), (gy, wy) = x, y
    if not weighted:
        wx, wy = np.ones(len(gx)), np.ones(len(gy))
    est = w1(gx, gy, wx, wy)
    stats = np.empty(n_boot)
    for i in range(n_boot):
        i1, i2 = rng.integers(0, len(gx), len(gx)), rng.integers(0, len(gy), len(gy))
        stats[i] = w1(gx[i1], gy[i2], wx[i1], wy[i2])
    lo, hi = _ci(stats)
    return {"w1": est, "lo": lo, "hi": hi}


def noise_floor(gen: np.ndarray, weights: np.ndarray, n_rep: int, rng: np.random.Generator,
                weighted: bool) -> Dict[str, float]:
    """W1 a perfect generator would show: samples of the measured size (and weights)
    drawn from the generated distribution, compared with that distribution."""
    stats = np.empty(n_rep)
    n = len(weights)
    for i in range(n_rep):
        s = rng.choice(gen, size=n, replace=True)
        stats[i] = w1(gen, s, None, rng.permutation(weights) if weighted else None)
    return {"median": float(np.median(stats)), "p95": float(np.percentile(stats, 95))}


def fixed_gap(gaps: np.ndarray, weights: np.ndarray, weighted: bool, gap_mm: float = FIXED_GAP_MM) -> float:
    w = weights if weighted else np.ones(len(gaps))
    return float(np.sum(w * np.abs(gaps - gap_mm)) / w.sum())


# --------------------------------------------------------------------------- report

def compare(contexts: Sequence[Dict], n_boot: int = 1000, seed: int = 0, n_floor: int = 500) -> Dict:
    gen_ctx = generated_samples(contexts)
    gen = np.concatenate(gen_ctx)
    rep: Dict = {"settings": {"n_boot": n_boot, "seed": seed, "n_floor": n_floor, "range_max_mm": RANGE_MAX_MM,
                              "kinds": "pipe-pipe", "surface": "bare"},
                 "generated": {"contexts": len(contexts), "contexts_with_pairs": int(sum(len(g) > 0 for g in gen_ctx)),
                               "pairs": int(len(gen)), "median_mm": float(np.median(gen)),
                               "p25_mm": float(np.percentile(gen, 25)), "p75_mm": float(np.percentile(gen, 75)),
                               "share_below_25mm": float(np.mean(gen < 25.0))},
                 "measured": {}, "gen_to_real": {}, "real_to_real": {}, "ducts": {}}
    samples = {}
    for name, label in PIPE_MODELS:
        rec = load_measured(name)
        g, w = measured_sample(rec)
        samples[name] = (g, w)
        rep["measured"][name] = {"label": label, "pairs": int(len(g)), "sections": int(w.sum()),
                                 "median_mm": float(np.median(g)), "length_weighted_median_mm": weighted_quantile(g, w, 0.5),
                                 "p25_mm": float(np.percentile(g, 25)), "p75_mm": float(np.percentile(g, 75)),
                                 "share_below_25mm": float(np.mean(g < 25.0)), "source": rec["source"]}
    for weighted in (True, False):
        key = "length_weighted" if weighted else "unweighted"
        rng = np.random.default_rng(seed)
        for name, _ in PIPE_MODELS:
            g, w = samples[name]
            r = gen_to_real(gen_ctx, g, w, n_boot, rng, weighted)
            r["noise_floor"] = noise_floor(gen, w, n_floor, rng, weighted)
            r["fixed_25mm"] = fixed_gap(g, w, weighted)
            rep["gen_to_real"].setdefault(name, {})[key] = r
        names = [n for n, _ in PIPE_MODELS]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                rep["real_to_real"].setdefault(f"{names[i]}|{names[j]}", {})[key] = real_to_real(
                    samples[names[i]], samples[names[j]], n_boot, rng, weighted)
    for name, label in DUCT_MODELS:
        rec = load_measured(name)
        g, w = measured_sample(rec, ("duct", "duct"))
        rep["ducts"][name] = {"label": label, "pairs": int(len(g)), "median_mm": float(np.median(g)) if len(g) else None,
                              "generated_duct_pairs": int(sum(len(x) for x in generated_samples(contexts, ("duct", "duct"))))}
    return rep


def load_segments(name: str) -> List[Dict]:
    with open(os.path.join(SEGMENTS_DIR, name + ".json")) as f:
        return json.load(f)["segments"]


def sensitivity(contexts: Sequence[Dict]) -> List[Dict]:
    """The comparison under other section-cut parameters, re-measured from the shipped
    segment tables (one parameter changed at a time)."""
    sys.path.insert(0, HERE)
    import measure_ifc as mi
    gen = np.concatenate(generated_samples(contexts))
    segs = {name: load_segments(name) for name, _ in PIPE_MODELS}
    rows = []
    for label, params in VARIATIONS:
        row = {"variation": label, "params": params, "models": {}}
        samples = {}
        for name, _ in PIPE_MODELS:
            g, w = measured_sample(mi.measure_segments(segs[name], name, **params))
            samples[name] = (g, w)
            row["models"][name] = {"pairs": int(len(g)), "w1_weighted": w1(gen, g, None, w), "w1_unweighted": w1(gen, g)}
        (gc, wc), (gd, wd) = samples["clinic_plumbing"], samples["duplex_mep"]
        row["clinic_to_duplex_mep_weighted"] = w1(gc, gd, wc, wd)
        rows.append(row)
    return rows


def render_sensitivity(rows: List[Dict]) -> str:
    L = ["Sensitivity to the section-cut parameters: W1 (mm), length-weighted / unweighted, and pairs",
         f"{'variation':<26}{'generated -> Clinic':>22}{'generated -> Duplex MEP':>26}{'generated -> Duplex Pl.':>26}{'Clinic <-> Duplex MEP':>24}"]
    for r in rows:
        cells = "".join(f"{m['w1_weighted']:>9.1f} /{m['w1_unweighted']:>6.1f} ({m['pairs']:>3})" for m in r["models"].values())
        L.append(f"{r['variation']:<26}{cells}{r['clinic_to_duplex_mep_weighted']:>14.1f}")
    return "\n".join(L)


def render(r: Dict) -> str:
    L: List[str] = []
    g = r["generated"]
    L.append(f"Pipe-pipe clear gaps between bare surfaces, < {r['settings']['range_max_mm']:g} mm. "
             f"Generated: {g['pairs']:,} pairs in {g['contexts_with_pairs']} of {g['contexts']:,} contexts, "
             f"median {g['median_mm']:.0f} mm (IQR {g['p25_mm']:.0f}-{g['p75_mm']:.0f}), {100 * g['share_below_25mm']:.0f} % below 25 mm")
    for name, m in r["measured"].items():
        L.append(f"  {m['label']:<24} {m['pairs']:>4} pairs on {m['sections']:>5} sections; median {m['median_mm']:.0f} mm "
                 f"(length-weighted {m['length_weighted_median_mm']:.0f}), IQR {m['p25_mm']:.0f}-{m['p75_mm']:.0f}, "
                 f"{100 * m['share_below_25mm']:.0f} % below 25 mm")
    for key, title in (("length_weighted", "pairs weighted by sections (primary)"), ("unweighted", "every pair once (sensitivity)")):
        L.append("")
        L.append(f"Wasserstein-1 (mm), {title}; 95 % bootstrap interval; noise floor = median (95th pct) for a perfect generator")
        for name, v in r["gen_to_real"].items():
            x = v[key]
            L.append(f"  generated -> {r['measured'][name]['label']:<24} {x['w1']:6.1f} ({x['lo']:.1f}-{x['hi']:.1f})"
                     f"   noise floor {x['noise_floor']['median']:.1f} ({x['noise_floor']['p95']:.1f})   fixed 25 mm gap {x['fixed_25mm']:.1f}")
        for pair, v in r["real_to_real"].items():
            a, b = pair.split("|")
            x = v[key]
            L.append(f"  {r['measured'][a]['label']} <-> {r['measured'][b]['label']}: {x['w1']:.1f} ({x['lo']:.1f}-{x['hi']:.1f})")
    for name, d in r["ducts"].items():
        L.append("")
        L.append(f"{d['label']}: {d['pairs']} duct-duct pairs, median {d['median_mm']:.0f} mm; not compared "
                 f"(the benchmark has {d['generated_duct_pairs']} duct-duct neighbour pairs)")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="dataset file (default: released benchmark)")
    ap.add_argument("--version", default=DATA_VERSION, help="data revision of the released benchmark")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--n-floor", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sensitivity", action="store_true", help="also re-measure under other section-cut parameters")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    payload = read_payload(a.file or split_path("benchmark", version=a.version))
    r = compare(payload["contexts"], a.n_boot, a.seed, a.n_floor)
    if a.sensitivity:
        r["sensitivity"] = sensitivity(payload["contexts"])
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(render(r))
        if a.sensitivity:
            print()
            print(render_sensitivity(r["sensitivity"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

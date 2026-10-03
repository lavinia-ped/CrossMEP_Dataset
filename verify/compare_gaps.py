#!/usr/bin/env python3
"""Distribution verification of clear gaps (paper section 5.2), fully reproducible.

Inputs
------
* ``verify/measured_gaps.json``           clear gaps (mm, surface-to-surface) between
                                          adjacent parallel runs measured on the open
                                          Duplex Apartment MEP model (``measure_ifc.py``)
* ``verify/measured_gaps_plumbing.json``  the same on the Plumbing discipline model
* a CrossMEP dataset file (default: the released benchmark split)

What is computed
----------------
1. The lognormal fit used by the generator: log-moments of the measured MEP gaps
   above the 25 mm clearance floor and below 600 mm (population std, n = 73), and
   a Kolmogorov-Smirnov test of that fit.  The generator constants
   ``GAP_LOGNORMAL_MU`` / ``GAP_LOGNORMAL_SIGMA`` must equal this fit.
2. Wasserstein-1 distances (gaps < 600 mm, the shared-support-plausible range)
   between generated and measured gap samples, for THREE definitions of the
   generated gap, because they are not the same quantity:

   * ``envelope``    the generator's sampled gap: clearance between the routing
                     envelopes (bare size + insulation + 25 mm per side).  This is
                     what the paper's Table 2 / section 5.2 report (41 mm).
   * ``insulation``  physical clear gap between insulation surfaces
                     (= envelope + 2 x 25 mm in the v3.0 geometry).
   * ``bare``        clear gap between bare element surfaces, the quantity the
                     IFC measurement actually produces (the Duplex model carries
                     no insulation geometry).

   The envelope definition is NOT like-for-like with the measurement; the
   like-for-like numbers are the ``bare`` (or ``insulation``) rows.  See
   README.md "Known issues" and VERIFICATION_LOG.md section 6.
3. Baselines: a fixed modular gap at the 25 mm floor, and the distance between
   the two real discipline models.

Only NumPy is required; SciPy, if installed, adds the KS p-value.

Usage::

    python verify/compare_gaps.py                      # released benchmark
    python verify/compare_gaps.py path/to/file.json    # any dataset file
    python verify/compare_gaps.py --json               # machine-readable
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Dict, List, Sequence

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import crossmep.tasks as cm  # noqa: E402
from crossmep.layout import GAP_FLOOR_MM, GAP_LOGNORMAL_MU, GAP_LOGNORMAL_SIGMA  # noqa: E402

MEASURED_MEP = os.path.join(HERE, "measured_gaps.json")
MEASURED_PLUMBING = os.path.join(HERE, "measured_gaps_plumbing.json")
RANGE_MAX_MM = 600.0          # shared-support-plausible range used throughout the paper
GAP_KINDS = ("envelope", "insulation", "bare")


def wasserstein_1(a: Sequence[float], b: Sequence[float]) -> float:
    """1-D Wasserstein-1 distance = integral of |F_a - F_b| (no SciPy needed)."""
    a, b = np.sort(np.asarray(a, float)), np.sort(np.asarray(b, float))
    allv = np.concatenate([a, b])
    allv.sort()
    deltas = np.diff(allv)
    ca = np.searchsorted(a, allv[:-1], side="right") / len(a)
    cb = np.searchsorted(b, allv[:-1], side="right") / len(b)
    return float(np.sum(np.abs(ca - cb) * deltas))


def ks_statistic_lognormal(x: Sequence[float], mu: float, sigma: float) -> float:
    x = np.sort(np.asarray(x, float))
    n = len(x)
    cdf = 0.5 * (1.0 + np.vectorize(math.erf)((np.log(x) - mu) / (sigma * math.sqrt(2.0))))
    d_plus = np.max(np.arange(1, n + 1) / n - cdf)
    d_minus = np.max(cdf - np.arange(0, n) / n)
    return float(max(d_plus, d_minus))


def ks_pvalue(d: float, n: int):
    """Two-sided exact KS p-value (SciPy's ``kstwo``); None without SciPy."""
    try:
        from scipy.stats import kstwo
    except ImportError:
        return None
    return float(kstwo.sf(d, n))


def fit_lognormal(mep_gaps: Sequence[float], floor: float = GAP_FLOOR_MM,
                  upper: float = RANGE_MAX_MM) -> Dict[str, float]:
    x = np.asarray(mep_gaps, float)
    pop = x[(x > floor) & (x < upper)]
    logs = np.log(pop)
    mu, sigma = float(logs.mean()), float(logs.std(ddof=0))
    d = ks_statistic_lognormal(pop, mu, sigma)
    return {"n": int(len(pop)), "mu": mu, "sigma": sigma, "ks_D": d, "ks_p": ks_pvalue(d, len(pop))}


def summarise(x: Sequence[float]) -> Dict[str, float]:
    x = np.asarray(x, float)
    return {"n": int(len(x)), "median": float(np.median(x)),
            "p25": float(np.percentile(x, 25)), "p75": float(np.percentile(x, 75)),
            "min": float(x.min()), "max": float(x.max())}


def compare(data: List[dict], mep: Sequence[float], plumbing: Sequence[float]) -> dict:
    mep, pl = np.asarray(mep, float), np.asarray(plumbing, float)
    mep6, pl6 = mep[mep < RANGE_MAX_MM], pl[pl < RANGE_MAX_MM]
    pooled = np.concatenate([mep6, pl6])
    out = {"range_max_mm": RANGE_MAX_MM,
           "measured": {"mep": summarise(mep6), "plumbing": summarise(pl6),
                        "mep_all": summarise(mep), "plumbing_all": summarise(pl)},
           "fit": fit_lognormal(mep),
           "generator_constants": {"mu": GAP_LOGNORMAL_MU, "sigma": GAP_LOGNORMAL_SIGMA, "floor_mm": GAP_FLOOR_MM},
           "generated": {}, "w1": {}, "baselines": {}}
    for kind in GAP_KINDS:
        g = np.array([v for c in data for v in cm.neighbour_gaps(c, kind)], float)
        g6 = g[g < RANGE_MAX_MM]
        out["generated"][kind] = summarise(g)
        out["w1"][kind] = {"mep": wasserstein_1(g6, mep6), "plumbing": wasserstein_1(g6, pl6),
                           "pooled": wasserstein_1(g6, pooled)}
    n_env = out["generated"]["envelope"]["n"]
    out["baselines"] = {"fixed_floor_gap_to_mep": wasserstein_1(np.full(n_env, GAP_FLOOR_MM), mep6),
                        "real_to_real": wasserstein_1(mep6, pl6),
                        "share_measured_mep_below_75mm": float(np.mean(mep6 < 3 * GAP_FLOOR_MM))}
    return out


def render(r: dict) -> str:
    L = []
    f, gc = r["fit"], r["generator_constants"]
    L.append(f"Lognormal fit to measured MEP gaps > {gc['floor_mm']:.0f} mm, < {r['range_max_mm']:.0f} mm: "
             f"n={f['n']}  mu={f['mu']:.3f}  sigma={f['sigma']:.3f}  KS D={f['ks_D']:.3f}"
             + (f"  p={f['ks_p']:.2f}" if f["ks_p"] is not None else "  (p needs SciPy)"))
    L.append(f"Generator constants: mu={gc['mu']}  sigma={gc['sigma']}  "
             f"{'MATCH' if abs(gc['mu']-f['mu']) < 5e-4 and abs(gc['sigma']-f['sigma']) < 5e-4 else 'MISMATCH'}")
    m = r["measured"]
    L.append(f"Measured (< {r['range_max_mm']:.0f} mm): MEP n={m['mep']['n']} median {m['mep']['median']:.0f} "
             f"IQR {m['mep']['p25']:.0f}-{m['mep']['p75']:.0f} | Plumbing n={m['plumbing']['n']} "
             f"median {m['plumbing']['median']:.0f} IQR {m['plumbing']['p25']:.0f}-{m['plumbing']['p75']:.0f}")
    L.append(f"{'generated gap definition':28s}{'n':>6}{'median':>8}{'IQR':>12}{'min':>7} | "
             f"{'W1->MEP':>8}{'W1->Plumb':>10}{'W1->pooled':>11}")
    for kind in GAP_KINDS:
        g, w = r["generated"][kind], r["w1"][kind]
        L.append(f"{kind:28s}{g['n']:>6}{g['median']:>8.0f}{g['p25']:>6.0f}-{g['p75']:<5.0f}{g['min']:>7.1f} | "
                 f"{w['mep']:>8.1f}{w['plumbing']:>10.1f}{w['pooled']:>11.1f}")
    b = r["baselines"]
    L.append(f"Baselines: fixed {gc['floor_mm']:.0f} mm gap -> MEP {b['fixed_floor_gap_to_mep']:.1f} mm; "
             f"MEP <-> Plumbing (real-to-real) {b['real_to_real']:.1f} mm; "
             f"share of measured MEP gaps below 75 mm: {100*b['share_measured_mep_below_75mm']:.0f}%")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="dataset file (default: released benchmark split)")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    a = ap.parse_args(argv)
    data = cm.load("benchmark") if a.file is None else json.load(open(a.file))["contexts"]
    with open(MEASURED_MEP) as f:
        mep = json.load(f)
    with open(MEASURED_PLUMBING) as f:
        pl = json.load(f)
    r = compare(data, mep, pl)
    print(json.dumps(r, indent=2) if a.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())

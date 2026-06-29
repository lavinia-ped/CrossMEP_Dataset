"""Wasserstein-1 verification of generated vs measured clear gaps (paper Section 5.2).

Reproduces the distance numbers reported in the paper directly from the released
files, with no hidden state:

  * generated clear gaps are recovered from the released context JSON (the actual
    realized gaps, not a re-draw): for two along-adjacent elements in the same
    row, gap = |center_a - center_b| - span_a/2 - span_b/2, where span is the
    along extent including insulation and the 2x25 mm routing clearance (the same
    `_span` the generator uses);
  * measured clear gaps are the Duplex MEP and Plumbing populations in
    measured_gaps.json / measured_gaps_plumbing.json;
  * the "fixed modular" baseline is the pre-fit generator, every gap pinned to the
    published 25 mm pipe-rack clearance floor.

All distributions are restricted to gaps < 600 mm (the shared-support-plausible
range) before the distance is taken, matching the paper.

Usage:
    python verify/wasserstein_gaps.py            # uses the train split (largest sample)
    python verify/wasserstein_gaps.py benchmark  # any released split

Reported in the paper (train split, v3.4):
    fixed-modular (25 mm floor) vs MEP : 139 mm
    fitted generator           vs MEP :  41 mm
    fitted generator           vs Plumbing : 89 mm
    fitted generator           vs pooled   : 59 mm
    real-real (MEP vs Plumbing)         :  50 mm   <- the synthetic-to-real
                                                      distance is comparable.
"""
from __future__ import annotations
import json, os, sys
from collections import defaultdict

import numpy as np
from scipy.stats import wasserstein_distance

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

CLEARANCE_MM = 25.0   # published pipe-rack clearance floor (must match generator)
GAP_CUTOFF_MM = 600.0  # shared-support-plausible range


def _span(e, surface_kind):
    """Along-surface extent of an element incl. insulation + 2x routing clearance.
    Identical to mep_context_sampler._span / crossmep_tasks._span."""
    along = e["width_mm"] if surface_kind == "ceiling" else e["height_mm"]
    return along + 2.0 * e["insulation_mm"] + 2.0 * CLEARANCE_MM


def generated_gaps(contexts):
    """Realized clear gaps between along-adjacent elements sharing a row."""
    gaps = []
    for c in contexts:
        sk = c["surface"]["kind"]
        rows = defaultdict(list)
        for e in c["elements"]:
            rows[e["level"]].append(e)
        for row in rows.values():
            row = sorted(row, key=lambda e: e["along_mm"])
            for a, b in zip(row, row[1:]):
                gap = abs(b["along_mm"] - a["along_mm"]) - _span(a, sk) / 2 - _span(b, sk) / 2
                gaps.append(gap)
    return np.asarray(gaps, dtype=float)


def _load_contexts(split, version="3.4"):
    path = os.path.join(_ROOT, f"mep_contexts_v{version}_{split}.json")
    return json.load(open(path))["contexts"]


def _load_measured(name):
    path = os.path.join(_HERE, name)
    return np.asarray([x for x in json.load(open(path)) if isinstance(x, (int, float))], float)


def _below(x, hi=GAP_CUTOFF_MM):
    x = np.asarray(x, float)
    return x[(x >= 0) & (x < hi)]


def main(split="train"):
    gen = _below(generated_gaps(_load_contexts(split)))
    mep = _below(_load_measured("measured_gaps.json"))
    plumb = _below(_load_measured("measured_gaps_plumbing.json"))
    pooled = np.concatenate([mep, plumb])
    fixed = np.full(5000, CLEARANCE_MM)   # pre-fit baseline: every gap at the floor

    def w1(a, b):
        return wasserstein_distance(a, b)

    print(f"split = {split}   (n generated gaps < {GAP_CUTOFF_MM:.0f} mm = {len(gen)})")
    print(f"measured: MEP n={len(mep)}, Plumbing n={len(plumb)}")
    print()
    print(f"  fixed-modular ({CLEARANCE_MM:.0f} mm floor)  vs MEP      : {w1(fixed, mep):5.1f} mm")
    print(f"  fitted generator                  vs MEP      : {w1(gen, mep):5.1f} mm")
    print(f"  fitted generator                  vs Plumbing : {w1(gen, plumb):5.1f} mm")
    print(f"  fitted generator                  vs pooled   : {w1(gen, pooled):5.1f} mm")
    print(f"  real-real (MEP vs Plumbing)                   : {w1(mep, plumb):5.1f} mm")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "train")

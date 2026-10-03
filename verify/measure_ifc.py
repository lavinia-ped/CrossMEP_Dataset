#!/usr/bin/env python3
"""Measure layout statistics of parallel MEP runs in an IFC model (IfcOpenShell).

This is the procedure described in ``verify/VERIFICATION.md`` and the paper
(section 4), written out with every parameter explicit:

1. Take every ``IfcFlowSegment``; read its nominal size from the ``Size``
   property (any property set) when present.
2. Mesh each segment in world coordinates; derive the long axis and the centre
   from the axis-aligned bounding box; keep HORIZONTAL segments (long axis x or
   y) longer than ``--min-length`` (250 mm).
3. Group parallel runs by axis and elevation band (``--z-band`` 400 mm); within
   a band, cluster across the axis with a ``--break`` (1.2 m) gap rule.  Per
   cluster report run multiplicity, in-bundle elevation spread (max - min of
   centre elevation) and the clear gaps between across-axis-adjacent runs
   (surface-to-surface = centre distance minus both half-extents across the
   axis).

Outputs a JSON report and, with ``--gaps-out``, the flat list of clear gaps in
the format of ``verify/measured_gaps.json``.

STATUS.  The shipped ``measured_gaps*.json`` are the authors' original
measurements (June 2026).  This script is the documented procedure made
executable; it was not re-run for release 3.5.0 because the Duplex Apartment
IFC files are not redistributed here (buildingSMART's sample-file repository has
since been reorganised; the files remain available from buildingSMART community
mirrors).  ``--self-check`` compares a fresh run with the shipped sample so that
anyone with the model can confirm or refute the numbers in one command.

Usage::

    pip install ifcopenshell
    python verify/measure_ifc.py Duplex_MEP.ifc --gaps-out gaps.json --self-check verify/measured_gaps.json
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np


def _settings():
    import ifcopenshell.geom
    s = ifcopenshell.geom.settings()
    try:                                   # IfcOpenShell >= 0.8
        s.set("use-world-coords", True)
    except Exception:                      # pragma: no cover - 0.7 API
        s.set(s.USE_WORLD_COORDS, True)
    return s


def _size_property(el) -> Optional[str]:
    try:
        import ifcopenshell.util.element as ue
        for pset in ue.get_psets(el).values():
            for k, v in pset.items():
                if k.lower() == "size" and v not in (None, ""):
                    return str(v)
    except Exception:
        return None
    return None


def segments(path: str, min_length_mm: float) -> List[Dict]:
    """Horizontal flow segments with centre, long axis, extents and nominal size."""
    import ifcopenshell
    import ifcopenshell.geom
    model = ifcopenshell.open(path)
    unit_scale = 1000.0                   # IfcOpenShell meshes in metres by default
    st = _settings()
    out: List[Dict] = []
    for el in model.by_type("IfcFlowSegment"):
        try:
            shape = ifcopenshell.geom.create_shape(st, el)
        except Exception:
            continue
        v = np.array(shape.geometry.verts, float).reshape(-1, 3) * unit_scale
        if len(v) == 0:
            continue
        lo, hi = v.min(axis=0), v.max(axis=0)
        ext = hi - lo
        axis = int(np.argmax(ext))
        if axis == 2 or ext[axis] < min_length_mm:
            continue                      # vertical riser or stub
        out.append({"id": el.GlobalId, "type": el.is_a(), "size": _size_property(el),
                    "axis": axis, "centre": ((lo + hi) / 2).tolist(), "extent": ext.tolist(),
                    "length_mm": float(ext[axis])})
    return out


def cluster(segs: List[Dict], z_band_mm: float, break_mm: float) -> List[List[Dict]]:
    """Group parallel runs: same long axis, same elevation band, across-axis gaps < break."""
    clusters: List[List[Dict]] = []
    for axis in (0, 1):
        across = 1 - axis
        runs = [s for s in segs if s["axis"] == axis]
        runs.sort(key=lambda s: s["centre"][2])
        bands: List[List[Dict]] = []
        for s in runs:
            if bands and s["centre"][2] - bands[-1][0]["centre"][2] <= z_band_mm:
                bands[-1].append(s)
            else:
                bands.append([s])
        for band in bands:
            band.sort(key=lambda s: s["centre"][across])
            cur = [band[0]]
            for a, b in zip(band, band[1:]):
                if b["centre"][across] - a["centre"][across] <= break_mm:
                    cur.append(b)
                else:
                    clusters.append(cur)
                    cur = [b]
            clusters.append(cur)
    return clusters


def analyse(clusters: List[List[Dict]]) -> Dict:
    gaps: List[float] = []
    spreads: List[float] = []
    multiplicity: List[int] = []
    for cl in clusters:
        multiplicity.append(len(cl))
        if len(cl) < 2:
            continue
        across = 1 - cl[0]["axis"]
        zs = [s["centre"][2] for s in cl]
        spreads.append(max(zs) - min(zs))
        for a, b in zip(cl, cl[1:]):
            centre = b["centre"][across] - a["centre"][across]
            gaps.append(centre - a["extent"][across] / 2 - b["extent"][across] / 2)
    g = np.array(gaps)
    g6 = g[g < 600] if len(g) else g
    return {"n_runs": int(sum(multiplicity)), "n_clusters": len(clusters),
            "multiplicity": {"p25": float(np.percentile(multiplicity, 25)),
                             "median": float(np.median(multiplicity)),
                             "p75": float(np.percentile(multiplicity, 75))},
            "elevation_spread_mm": {"median": float(np.median(spreads)) if spreads else None,
                                    "p75": float(np.percentile(spreads, 75)) if spreads else None},
            "clear_gaps_mm": {"n": int(len(g)), "n_below_600": int(len(g6)),
                              "median": float(np.median(g6)) if len(g6) else None,
                              "p25": float(np.percentile(g6, 25)) if len(g6) else None,
                              "p75": float(np.percentile(g6, 75)) if len(g6) else None},
            "gaps": [float(x) for x in gaps]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ifc")
    ap.add_argument("--min-length", type=float, default=250.0, help="mm (default 250)")
    ap.add_argument("--z-band", type=float, default=400.0, help="elevation band, mm (default 400)")
    ap.add_argument("--break", dest="brk", type=float, default=1200.0, help="across-axis cluster break, mm (default 1200)")
    ap.add_argument("--gaps-out", help="write the flat clear-gap list here (measured_gaps.json format)")
    ap.add_argument("--self-check", help="compare with a shipped measured_gaps*.json")
    a = ap.parse_args(argv)
    try:
        import ifcopenshell  # noqa: F401
    except ImportError:
        print("ifcopenshell is required: pip install ifcopenshell", file=sys.stderr)
        return 2
    segs = segments(a.ifc, a.min_length)
    sizes = sorted({s["size"] for s in segs if s["size"]})
    rep = analyse(cluster(segs, a.z_band, a.brk))
    rep["sizes_present"] = sizes
    gaps = rep.pop("gaps")
    print(json.dumps(rep, indent=2))
    if a.gaps_out:
        with open(a.gaps_out, "w") as f:
            json.dump(gaps, f)
    if a.self_check:
        with open(a.self_check) as f:
            ref = np.array(json.load(f))
        g = np.array(gaps)
        print(f"self-check vs {a.self_check}: n {len(g)} vs {len(ref)}; "
              f"median(<600) {np.median(g[g<600]):.1f} vs {np.median(ref[ref<600]):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

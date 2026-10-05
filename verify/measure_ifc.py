#!/usr/bin/env python3
"""Measure clear gaps between side-by-side MEP runs in an IFC model, on sections.

A CrossMEP context is the section across a run at one support.  The measurement
therefore cuts the model the same way and records what such a section shows:

1. Mesh every ``IfcFlowSegment`` in world coordinates (IfcOpenShell) and record its
   kind (pipe, duct, cable carrier, from its type object), its ``Size`` property
   and its bounding box; the plan direction of its long axis comes from a
   principal-component fit of the mesh vertices.
2. Keep **horizontal, axis-aligned runs**: plan direction within ``--angle-tol``
   (2 degrees) of the x or y axis, length >= ``--min-length`` (250 mm), and longer
   than they are tall (risers are dropped).  Diagonal runs are dropped.
3. **Cut sections** perpendicular to each axis every ``--step`` mm (250).  A run is
   in a section if the section plane passes through it.  Within a section, runs
   whose centres lie within ``--band`` mm (400) of the lowest run of the band form
   one row (the generator's row, which allows a stagger of up to 120 mm).
4. Along each row, sorted across the axis, two consecutive runs are **neighbours**
   if their clear gap (centre distance minus both half-widths, i.e. between bare
   surfaces) is positive and below ``--break`` mm (1,200; wider is a different
   bundle).  Non-positive gaps are runs that cross over or under each other inside
   the band; they are counted, not used.
5. Every neighbour pair is reported once with its gap (median over the sections it
   appears in), the number of sections (its overlap length / step) and both kinds.
   Weighting a pair by its sections gives the gap a support designer meets at a
   random hanger location; the unweighted pairs are a sensitivity check.

Output: a JSON record with the pairs, a summary and the provenance (file name,
SHA-256 and size of the IFC file, IfcOpenShell version, every parameter), and
optionally the meshed segment table (bounding boxes to 0.1 mm), from which
``measure_segments`` recomputes the record without IfcOpenShell.
``verify/measured/`` holds the records for the open buildingSMART Duplex Apartment
and Medical-Dental Clinic models (CC BY 4.0, see ``verify/measured/README.md``).

The procedure documented in June 2026 (``--legacy``: group runs by elevation
band, cluster across the axis, take gaps between across-sorted neighbours) is kept
for transparency.  It does not require two runs to pass through a common section
and pairs the collinear pieces of one run, so on the Duplex MEP model it returns
negative "gaps" (median -24 mm) and does not reproduce the shipped
``measured_gaps.json``; see ``verify/VERIFICATION.md``.

Usage::

    pip install ifcopenshell
    python verify/measure_ifc.py Duplex_MEP_20110907.ifc --name duplex_mep \\
        --out verify/measured/duplex_mep.json --segments-out verify/measured/segments/duplex_mep.json
    python verify/measure_ifc.py Duplex_MEP_20110907.ifc --legacy        # the June 2026 procedure
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

PROCEDURE = "section-cut 1.0"
DEFAULTS = {"min_length_mm": 250.0, "angle_tol_deg": 2.0, "step_mm": 250.0, "band_mm": 400.0, "break_mm": 1200.0}


# --------------------------------------------------------------------------- IFC part (needs IfcOpenShell)

def _settings():
    import ifcopenshell.geom
    s = ifcopenshell.geom.settings()
    try:                                   # IfcOpenShell >= 0.8
        s.set("use-world-coords", True)
    except Exception:                      # pragma: no cover - 0.7 API
        s.set(s.USE_WORLD_COORDS, True)
    return s


def _kind(el) -> str:
    import ifcopenshell.util.element as ue
    t = ue.get_type(el)
    name = t.is_a() if t is not None else ""
    for key, kind in (("Pipe", "pipe"), ("Duct", "duct"), ("CableCarrier", "cable_carrier")):
        if key in name:
            return kind
    ot = (el.ObjectType or "").lower()
    if "pipe" in ot:
        return "pipe"
    if "duct" in ot:
        return "duct"
    if any(k in ot for k in ("conduit", "tray", "cable")):
        return "cable_carrier"
    return "other"


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


def _plan_angle(v: np.ndarray) -> float:
    """Plan direction of the long axis, degrees in [0, 180), from the mesh vertices."""
    p = v[:, :2] - v[:, :2].mean(axis=0)
    if not np.any(p):
        return 0.0
    _, _, vt = np.linalg.svd(p, full_matrices=False)
    return math.degrees(math.atan2(vt[0][1], vt[0][0])) % 180.0


def mesh_segments(path: str) -> List[Dict]:
    """Every IfcFlowSegment: GlobalId, kind, size, bounding box (mm), plan angle."""
    import multiprocessing

    import ifcopenshell
    import ifcopenshell.geom
    model = ifcopenshell.open(path)
    els = model.by_type("IfcFlowSegment")
    by_id = {e.id(): e for e in els}
    out: List[Dict] = []

    def add(el, verts):
        v = np.asarray(verts, float).reshape(-1, 3) * 1000.0      # IfcOpenShell meshes in metres
        if len(v):
            out.append({"gid": el.GlobalId, "kind": _kind(el), "size": _size_property(el),
                        "lo": v.min(axis=0).tolist(), "hi": v.max(axis=0).tolist(), "angle_deg": _plan_angle(v)})

    if not els:
        return out
    it = ifcopenshell.geom.iterator(_settings(), model, multiprocessing.cpu_count(), include=els)
    if it.initialize():
        while True:
            sh = it.get()
            add(by_id.get(sh.id) or model.by_id(sh.id), sh.geometry.verts)
            if not it.next():
                break
    return out


# --------------------------------------------------------------------------- section cut (pure Python + NumPy)

def horizontal_runs(segments: Iterable[Dict], min_length_mm: float = DEFAULTS["min_length_mm"],
                    angle_tol_deg: float = DEFAULTS["angle_tol_deg"]) -> List[Dict]:
    """Horizontal, axis-aligned runs with along-interval [a0, a1], across centre u,
    across width w, centre elevation z and height h (all mm)."""
    runs: List[Dict] = []
    for s in segments:
        a = s["angle_deg"] % 180.0
        if min(a, 180.0 - a) <= angle_tol_deg:
            axis = 0
        elif abs(a - 90.0) <= angle_tol_deg:
            axis = 1
        else:
            continue                                   # diagonal in plan
        lo, hi = s["lo"], s["hi"]
        length, width, height = hi[axis] - lo[axis], hi[1 - axis] - lo[1 - axis], hi[2] - lo[2]
        if length < min_length_mm or height > length:
            continue                                   # stub or riser
        runs.append({"gid": s["gid"], "kind": s["kind"], "size": s.get("size"), "axis": axis,
                     "a0": lo[axis], "a1": hi[axis], "u": (lo[1 - axis] + hi[1 - axis]) / 2.0, "w": width,
                     "z": (lo[2] + hi[2]) / 2.0, "h": height})
    return runs


def section_gaps(runs: Sequence[Dict], step_mm: float = DEFAULTS["step_mm"], band_mm: float = DEFAULTS["band_mm"],
                 break_mm: float = DEFAULTS["break_mm"]) -> Tuple[List[Dict], Dict]:
    """Neighbour gaps on every section.  Returns (records, counts): one record per
    (section, neighbour pair) and counts of sections, crossing pairs and row bundles."""
    records: List[Dict] = []
    counts = {"sections": 0, "crossing_pairs": 0, "row_bundle_sizes": Counter()}
    for axis in (0, 1):
        S = [r for r in runs if r["axis"] == axis]
        if not S:
            continue
        t0, t1 = min(r["a0"] for r in S), max(r["a1"] for r in S)
        for t in np.arange(t0 + step_mm / 2.0, t1, step_mm):
            cut = sorted((r for r in S if r["a0"] < t < r["a1"]), key=lambda r: (r["z"], r["u"], r["gid"]))
            if not cut:
                continue
            counts["sections"] += 1
            rows: List[List[Dict]] = []
            for r in cut:
                if rows and r["z"] - rows[-1][0]["z"] <= band_mm:
                    rows[-1].append(r)
                else:
                    rows.append([r])
            for row in rows:
                row.sort(key=lambda r: (r["u"], r["gid"]))
                bundle = 1
                for a, b in zip(row, row[1:]):
                    gap = (b["u"] - b["w"] / 2.0) - (a["u"] + a["w"] / 2.0)
                    if gap >= break_mm:
                        counts["row_bundle_sizes"][bundle] += 1
                        bundle = 1
                        continue
                    bundle += 1
                    if gap <= 0.0:
                        counts["crossing_pairs"] += 1
                        continue
                    records.append({"axis": axis, "t_mm": float(t), "a": a["gid"], "b": b["gid"],
                                    "kinds": sorted((a["kind"], b["kind"])), "gap_mm": float(gap)})
                counts["row_bundle_sizes"][bundle] += 1
    return records, counts


def pair_table(records: Iterable[Dict]) -> List[Dict]:
    """One row per neighbour pair: median gap over its sections, the number of
    sections (its length weight), min and max gap and both kinds."""
    by: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for r in records:
        by[tuple(sorted((r["a"], r["b"])))].append(r)
    out = []
    for (a, b), rs in sorted(by.items()):
        g = [r["gap_mm"] for r in rs]
        out.append({"a": a, "b": b, "kinds": rs[0]["kinds"], "gap_mm": round(float(np.median(g)), 2),
                    "gap_min_mm": round(min(g), 2), "gap_max_mm": round(max(g), 2), "n_sections": len(rs)})
    return out


def summarise(pairs: Sequence[Dict], range_max_mm: float = 600.0) -> Dict:
    def stats(rows):
        g = np.array([p["gap_mm"] for p in rows if p["gap_mm"] < range_max_mm])
        w = np.array([p["n_sections"] for p in rows if p["gap_mm"] < range_max_mm], float)
        if not len(g):
            return {"pairs": 0}
        o = np.argsort(g)
        cw = np.cumsum(w[o]) / w.sum()
        wq = lambda q: float(g[o][np.searchsorted(cw, q)])
        return {"pairs": int(len(g)), "median_mm": float(np.median(g)), "p25_mm": float(np.percentile(g, 25)),
                "p75_mm": float(np.percentile(g, 75)), "length_weighted_median_mm": wq(0.5),
                "share_below_25mm": float(np.mean(g < 25.0))}
    kinds = Counter("-".join(p["kinds"]) for p in pairs)
    return {"all": stats(pairs), "pipe-pipe": stats([p for p in pairs if p["kinds"] == ["pipe", "pipe"]]),
            "pairs_by_kind": dict(kinds)}


def round_segments(segments: Iterable[Dict]) -> List[Dict]:
    """The shipped segment table: bounding boxes to 0.1 mm, angles to 1e-4 degree."""
    return [{"gid": s["gid"], "kind": s["kind"], "size": s["size"], "lo": [round(x, 1) for x in s["lo"]],
             "hi": [round(x, 1) for x in s["hi"]], "angle_deg": round(s["angle_deg"], 4)}
            for s in sorted(segments, key=lambda s: s["gid"])]


def measure_segments(segments: Sequence[Dict], name: str, source: Optional[Dict] = None, **params) -> Dict:
    """The section-cut record of a segment table (no IfcOpenShell needed)."""
    p = {**DEFAULTS, **{k: v for k, v in params.items() if v is not None}}
    runs = horizontal_runs(segments, p["min_length_mm"], p["angle_tol_deg"])
    records, counts = section_gaps(runs, p["step_mm"], p["band_mm"], p["break_mm"])
    pairs = pair_table(records)
    return {"name": name, "source": source or {}, "procedure": {"version": PROCEDURE, **p},
            "counts": {"flow_segments": len(segments), "horizontal_runs": len(runs),
                       "runs_by_kind": dict(sorted(Counter(r["kind"] for r in runs).items())),
                       "sections": counts["sections"], "crossing_pairs": counts["crossing_pairs"],
                       "row_bundle_sizes": {str(k): v for k, v in sorted(counts["row_bundle_sizes"].items())}},
            "summary": summarise(pairs), "pairs": pairs}


def measure(path: str, name: Optional[str] = None, **params) -> Tuple[Dict, List[Dict]]:
    """Mesh an IFC file and measure it: (record, rounded segment table)."""
    import ifcopenshell
    segs = round_segments(mesh_segments(path))
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    source = {"file": os.path.basename(path), "sha256": digest, "bytes": os.path.getsize(path),
              "ifcopenshell": ifcopenshell.version}
    return measure_segments(segs, name or os.path.splitext(os.path.basename(path))[0], source, **params), segs


# --------------------------------------------------------------------------- the June 2026 procedure (legacy)

def legacy_segments(path: str, min_length_mm: float) -> List[Dict]:
    """Horizontal flow segments with centre, long axis (bounding box) and extents."""
    out: List[Dict] = []
    for s in mesh_segments(path):
        lo, hi = np.array(s["lo"]), np.array(s["hi"])
        ext = hi - lo
        axis = int(np.argmax(ext))
        if axis == 2 or ext[axis] < min_length_mm:
            continue
        out.append({"id": s["gid"], "size": s["size"], "axis": axis, "centre": ((lo + hi) / 2).tolist(),
                    "extent": ext.tolist(), "length_mm": float(ext[axis])})
    return out


def cluster(segs: List[Dict], z_band_mm: float, break_mm: float) -> List[List[Dict]]:
    """Legacy: group parallel runs by long axis, elevation band and across-axis break."""
    clusters: List[List[Dict]] = []
    for axis in (0, 1):
        across = 1 - axis
        runs = sorted((s for s in segs if s["axis"] == axis), key=lambda s: s["centre"][2])
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
    """Legacy: gaps between across-sorted neighbours of each cluster."""
    gaps: List[float] = []
    multiplicity: List[int] = []
    for cl in clusters:
        multiplicity.append(len(cl))
        across = 1 - cl[0]["axis"]
        for a, b in zip(cl, cl[1:]):
            gaps.append(b["centre"][across] - a["centre"][across] - a["extent"][across] / 2 - b["extent"][across] / 2)
    g = np.array(gaps)
    g6 = g[g < 600] if len(g) else g
    return {"n_runs": int(sum(multiplicity)), "n_clusters": len(clusters),
            "clear_gaps_mm": {"n": int(len(g)), "n_below_600": int(len(g6)),
                              "median": float(np.median(g6)) if len(g6) else None},
            "gaps": [float(x) for x in gaps]}


# --------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ifc")
    ap.add_argument("--out", help="write the JSON record here (default: print the summary only)")
    ap.add_argument("--segments-out", help="also write the meshed segment table (re-measurable without IfcOpenShell)")
    ap.add_argument("--name", help="name stored in the record (default: the file stem)")
    ap.add_argument("--min-length", type=float, help=f"mm (default {DEFAULTS['min_length_mm']:g})")
    ap.add_argument("--angle-tol", type=float, help=f"degrees (default {DEFAULTS['angle_tol_deg']:g})")
    ap.add_argument("--step", type=float, help=f"section spacing, mm (default {DEFAULTS['step_mm']:g})")
    ap.add_argument("--band", type=float, help=f"row elevation band, mm (default {DEFAULTS['band_mm']:g})")
    ap.add_argument("--break", dest="brk", type=float, help=f"bundle break, mm (default {DEFAULTS['break_mm']:g})")
    ap.add_argument("--legacy", action="store_true", help="run the June 2026 procedure instead (kept for transparency)")
    ap.add_argument("--self-check", help="with --legacy: compare with a shipped measured_gaps*.json")
    a = ap.parse_args(argv)
    try:
        import ifcopenshell  # noqa: F401
    except ImportError:
        print("ifcopenshell is required: pip install ifcopenshell", file=sys.stderr)
        return 2
    if a.legacy:
        rep = analyse(cluster(legacy_segments(a.ifc, a.min_length or 250.0), a.band or 400.0, a.brk or 1200.0))
        gaps = np.array(rep.pop("gaps"))
        print(json.dumps(rep, indent=2))
        if a.self_check:
            with open(a.self_check) as f:
                ref = np.array(json.load(f))
            print(f"self-check vs {a.self_check}: n {len(gaps)} vs {len(ref)}; "
                  f"median(<600) {np.median(gaps[gaps < 600]):.1f} vs {np.median(ref[ref < 600]):.1f}")
        return 0
    rec, segs = measure(a.ifc, a.name, min_length_mm=a.min_length, angle_tol_deg=a.angle_tol, step_mm=a.step,
                        band_mm=a.band, break_mm=a.brk)
    print(json.dumps({k: rec[k] for k in ("name", "source", "procedure", "counts", "summary")}, indent=1))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(rec, f, indent=1)
    if a.segments_out:
        with open(a.segments_out, "w") as f:
            json.dump({"name": rec["name"], "source": rec["source"], "segments": segs}, f, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""What a hanger carries in the open buildings, against what the generator draws.

The gap comparison (``compare_sections.py``) tests how close neighbours sit.  This
script tests the *composition* the generator declares rather than measures: how
many elements share one support location, which kinds they are, how often kinds
mix in one bundle, how often rows are stacked, and which pipe sizes occur.

Measured side: the shipped segment tables (``verify/measured/segments/``) of the
buildingSMART models, cut into sections every 250 mm exactly as for the gaps
(``measure_ifc.section_bundles``).  Disciplines of one building are merged before
cutting, so a bundle can mix kinds:

* Clinic: Plumbing + HVAC models (pipes and ducts).  The Electrical model holds
  fixtures only (no IfcFlowSegment), so containment is absent from the measured
  clinic.
* Duplex: MEP model alone (pipes and six conduit runs).  The Plumbing model
  re-exports most of the MEP model's pipes (161 of its 231 segments have the
  same bounding box) and is not merged, to avoid double counting; the Electrical
  model holds fixtures only.

Each (section, bundle) record is one hanger location, 250 mm of run apart, so
shares are length-weighted; 95 % intervals come from a bootstrap over physical
bundles (the sets of runs that travel together), the independent units.

Generated side: the released benchmark, one context = one bundle, **restricted to
the kinds the measured building models** (for the clinic: contexts of pipes and
ducts only), since a kind the model does not contain cannot be compared.  Tiers
are uniform by construction, so composition is compared *conditional on the
count*: for n = 2 ... 8 the kind shares, the mixed-kind share and the stacked
share, measured against generated; bundle sizes themselves are reported for
information.  Pipe sizes are compared as the share of each DN of the generator's
series (nearest series size; real sizes above DN100 form a separate bin).

What cannot be tested here: the electrical share (no containment runs in the open
models beyond six duplex conduits) and the mounting surface (no architecture model
is used), so both stay declared.  The comparison is descriptive: it says where the
declared composition is near practice and where it is not; nothing is fitted.

Usage::

    python verify/compare_composition.py
    python verify/compare_composition.py --json
    python verify/compare_composition.py --n-boot 200
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import measure_ifc as mi  # noqa: E402
from crossmep.io import DATA_VERSION, read_payload, split_path  # noqa: E402
from crossmep.library import DN_OD_MM, DN_SERIES  # noqa: E402

SEGMENTS_DIR = os.path.join(HERE, "measured", "segments")
BUILDINGS = (("clinic", "Clinic (Plumbing + HVAC)", ("clinic_plumbing", "clinic_hvac")),
             ("duplex", "Duplex (MEP)", ("duplex_mep",)))
KINDS = ("pipe", "duct", "electrical")        # measured kinds; generated trays and conduits are 'electrical'
COUNTS = tuple(range(1, 9))                   # bundle sizes reported; 8 = eight or more
DN_BINS = tuple(str(d) for d in DN_SERIES) + (">100",)
SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*mm")

# columns of the per-bundle count table: per count k, [locations, mixed, stacked, pipe, duct, electrical]
_PER_K = 6
_DN0 = _PER_K * len(COUNTS)
_NCOL = _DN0 + len(DN_BINS)


# --------------------------------------------------------------------------- measured

def load_segments(name: str) -> List[Dict]:
    with open(os.path.join(SEGMENTS_DIR, name + ".json")) as f:
        return json.load(f)["segments"]


def measured_bundles(names: Sequence[str], **params) -> List[Dict]:
    """Section bundles of the merged segment tables; kinds mapped to KINDS, pipe
    sizes to DN bins."""
    p = {**mi.DEFAULTS, "stack_mm": mi.STACK_MM, **{k: v for k, v in params.items() if v is not None}}
    segs = [s for n in names for s in load_segments(n)]
    runs = mi.horizontal_runs(segs, p["min_length_mm"], p["angle_tol_deg"])
    out = mi.section_bundles(runs, p["step_mm"], p["band_mm"], p["break_mm"], p["stack_mm"])
    for b in out:
        b["kinds"] = ["electrical" if k == "cable_carrier" else k for k in b["kinds"]]
        b["dns"] = [d for d in (dn_bin(s) for s, k in zip(b["sizes"], b["kinds"]) if k == "pipe") if d]
    return out


def dn_bin(size: Optional[str]) -> Optional[str]:
    """Nearest generator DN for a Revit-style size string ('80 mmø'); None if unknown."""
    if not size:
        return None
    m = SIZE_RE.match(size)
    if not m:
        return None
    d = float(m.group(1))
    if d > DN_SERIES[-1] * 1.1:
        return ">100"
    return str(min(DN_SERIES, key=lambda s: abs(s - d)))


# --------------------------------------------------------------------------- generated

def generated_bundles(contexts: Sequence[Dict], kinds_present: Optional[Sequence[str]] = None) -> List[Dict]:
    """One bundle per context; with ``kinds_present`` only contexts made of those kinds."""
    out = []
    for c in contexts:
        kinds = ["electrical" if e["kind"] in ("cable_tray", "conduit") else e["kind"] for e in c["elements"]]
        if kinds_present is not None and not set(kinds) <= set(kinds_present):
            continue
        dns = [str(min(DN_SERIES, key=lambda s: abs(_dn_of(e) - s))) for e in c["elements"] if e["kind"] == "pipe"]
        out.append({"n": len(kinds), "kinds": kinds, "stack": len({e["level"] for e in c["elements"]}),
                    "dns": dns, "gids": (c["context_id"],)})
    return out


def _dn_of(e: Dict) -> float:
    return min(DN_OD_MM, key=lambda dn: abs(DN_OD_MM[dn] - e["width_mm"]))


# --------------------------------------------------------------------------- statistics

def table(bundles: Sequence[Dict]) -> np.ndarray:
    """Per physical bundle, the counts every statistic needs (rows sum to a sample)."""
    index: Dict[tuple, int] = {}
    rows: List[np.ndarray] = []
    for b in bundles:
        i = index.get(b["gids"])
        if i is None:
            i = index[b["gids"]] = len(rows)
            rows.append(np.zeros(_NCOL))
        r = rows[i]
        k = min(b["n"], COUNTS[-1]) - 1
        base = k * _PER_K
        r[base] += 1
        r[base + 1] += len(set(b["kinds"])) > 1
        r[base + 2] += b["stack"] > 1
        for kd in b["kinds"]:
            r[base + 3 + KINDS.index(kd)] += 1
        for d in b["dns"]:
            r[_DN0 + DN_BINS.index(d)] += 1
    return np.array(rows) if rows else np.zeros((0, _NCOL))


def shares(v: np.ndarray) -> Dict:
    """Composition statistics from a summed count row."""
    loc = np.array([v[(k - 1) * _PER_K] for k in COUNTS])
    out: Dict = {"locations": int(loc.sum()),
                 "size_share": {str(k): float(loc[i] / loc.sum()) if loc.sum() else 0.0 for i, k in enumerate(COUNTS)},
                 "by_count": {}}
    for k in COUNTS[1:]:
        base = (k - 1) * _PER_K
        n = v[base]
        if n == 0:
            out["by_count"][str(k)] = None
            continue
        kc = v[base + 3: base + 6]
        out["by_count"][str(k)] = {"locations": int(n), "kind_share": {kd: float(kc[i] / kc.sum()) for i, kd in enumerate(KINDS)},
                                   "mixed_share": float(v[base + 1] / n), "stacked_share": float(v[base + 2] / n)}
    dn = v[_DN0:]
    out["dn_share"] = {d: float(dn[i] / dn.sum()) if dn.sum() else 0.0 for i, d in enumerate(DN_BINS)}
    out["dn_known"] = int(dn.sum())
    return out


def tv(p: Dict[str, float], q: Dict[str, float]) -> float:
    """Total-variation distance between two share vectors over the same keys."""
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in set(p) | set(q))


def bootstrap(T: np.ndarray, stat, n_boot: int, seed: int) -> Tuple[float, float]:
    """Percentile interval of ``stat(shares(sum))`` resampling physical bundles (rows of T)."""
    rng = np.random.default_rng(seed)
    G = len(T)
    vals = [stat(shares(rng.multinomial(G, np.full(G, 1.0 / G)) @ T)) for _ in range(n_boot)]
    return float(np.nanpercentile(vals, 2.5)), float(np.nanpercentile(vals, 97.5))


def compare(contexts: Sequence[Dict], n_boot: int = 500, seed: int = 0, **params) -> Dict:
    rep: Dict = {"generated_all": shares(table(generated_bundles(contexts)).sum(axis=0)), "measured": {}}
    for key, label, names in BUILDINGS:
        meas = measured_bundles(names, **params)
        present = sorted({k for b in meas for k in b["kinds"]})
        gen = generated_bundles(contexts, present)
        g = shares(table(gen).sum(axis=0))
        T = table(meas)
        s = shares(T.sum(axis=0))
        s.update({"label": label, "models": list(names), "kinds_present": present, "physical_bundles": int(len(T)),
                  "generated": g, "generated_contexts": len(gen), "distance_by_count": {}})
        for k in COUNTS[1:]:
            m, gg = s["by_count"][str(k)], g["by_count"][str(k)]
            if m is None or gg is None:
                continue

            def kind_tv(sh, k=str(k), ref=gg["kind_share"]):
                return tv(sh["by_count"][k]["kind_share"], ref) if sh["by_count"][k] else float("nan")
            lo, hi = bootstrap(T, kind_tv, n_boot, seed)
            s["distance_by_count"][str(k)] = {"kind_tv": tv(m["kind_share"], gg["kind_share"]), "kind_tv_ci": [lo, hi],
                                              "mixed_diff": m["mixed_share"] - gg["mixed_share"],
                                              "stacked_diff": m["stacked_share"] - gg["stacked_share"]}
        s["dn_tv"] = tv(s["dn_share"], g["dn_share"])
        s["dn_tv_ci"] = list(bootstrap(T, lambda sh: tv(sh["dn_share"], g["dn_share"]), n_boot, seed))
        rep["measured"][key] = s
    keys = list(rep["measured"])
    rep["real_to_real_dn_tv"] = {f"{a}<->{b}": tv(rep["measured"][a]["dn_share"], rep["measured"][b]["dn_share"])
                                 for i, a in enumerate(keys) for b in keys[i + 1:]}
    return rep


# --------------------------------------------------------------------------- report

def render(rep: Dict) -> str:
    L = ["Hanger locations: what one support carries, sections every 250 mm (length-weighted); generated = benchmark "
         "contexts made of the kinds the building models", ""]
    L.append("Bundle size at a hanger location (share of locations; the benchmark is uniform over 1-8 by construction)")
    L.append("  " + "size".ljust(28) + "".join(f"{k:>7}" for k in COUNTS[:-1]) + f"{'8+':>7}")
    for s in rep["measured"].values():
        L.append("  " + s["label"].ljust(28) + "".join(f"{100 * s['size_share'][str(k)]:6.0f}%" for k in COUNTS))
    L.append("")
    L.append("Conditional on the count n: element kinds (pipe / duct / electrical), bundles mixing kinds, bundles with another "
             "row stacked within 1.5 m")
    for s in rep["measured"].values():
        g = s["generated"]
        L.append(f"  {s['label']}: kinds present {', '.join(s['kinds_present'])}; {s['locations']:,} locations, "
                 f"{s['physical_bundles']:,} physical bundles; generated reference {s['generated_contexts']:,} contexts")
        L.append("    n   locations   measured pipe/duct/elec   generated pipe/duct/elec   TV (95 %)        "
                 "mixed meas/gen   stacked meas/gen")
        for k in COUNTS[1:]:
            m, gg, d = s["by_count"][str(k)], g["by_count"][str(k)], s["distance_by_count"].get(str(k))
            if m is None or d is None:
                L.append(f"    {k}   {'-':>9}   (no measured bundle of this size)")
                continue
            ms = "/".join(f"{100 * m['kind_share'][kd]:3.0f}" for kd in KINDS)
            gs = "/".join(f"{100 * gg['kind_share'][kd]:3.0f}" for kd in KINDS)
            L.append(f"    {k}   {m['locations']:>9,}   {ms:>23}   {gs:>24}   "
                     f"{d['kind_tv']:.2f} ({d['kind_tv_ci'][0]:.2f}-{d['kind_tv_ci'][1]:.2f})   "
                     f"{100 * m['mixed_share']:3.0f}% / {100 * gg['mixed_share']:3.0f}%       "
                     f"{100 * m['stacked_share']:3.0f}% / {100 * gg['stacked_share']:3.0f}%")
    L.append("")
    L.append("Pipe sizes (share of pipes by nearest generator DN; TV = total-variation distance to the generated shares)")
    L.append("  " + "DN".ljust(34) + "".join(f"{d:>6}" for d in DN_BINS) + "   TV (95 %)")
    ga = rep["generated_all"]
    L.append("  " + "generated (all contexts)".ljust(34) + "".join(f"{100 * ga['dn_share'][d]:5.0f}%" for d in DN_BINS))
    for s in rep["measured"].values():
        L.append("  " + f"{s['label']} (n={s['dn_known']:,})".ljust(34)
                 + "".join(f"{100 * s['dn_share'][d]:5.0f}%" for d in DN_BINS)
                 + f"   {s['dn_tv']:.2f} ({s['dn_tv_ci'][0]:.2f}-{s['dn_tv_ci'][1]:.2f})")
    for pair, d in rep["real_to_real_dn_tv"].items():
        a, b = pair.split("<->")
        L.append(f"  {rep['measured'][a]['label']} <-> {rep['measured'][b]['label']}: TV {d:.2f} (real to real)")
    L.append("")
    L.append("Not testable on these models: the electrical share (the open electrical models carry fixtures only; the duplex MEP "
             "model has six conduit runs)")
    L.append("and the mounting surface (no architecture model is used). TV = 0 identical shares, 1 disjoint.")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="dataset file (default: released benchmark)")
    ap.add_argument("--version", default=DATA_VERSION, help="data revision of the released benchmark")
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    contexts = read_payload(a.file or split_path("benchmark", version=a.version))["contexts"]
    rep = compare(contexts, n_boot=a.n_boot, seed=a.seed)
    print(json.dumps(rep, indent=1) if a.json else render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())

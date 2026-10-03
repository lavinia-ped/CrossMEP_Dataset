"""Loader and dataset-native benchmark tasks -- standard library only.

Third parties can produce comparable numbers from the released JSON files
without NumPy or the generator::

    import crossmep.tasks as cm
    data = cm.load("benchmark")                     # list of context dicts (revision 4.0)
    print(cm.per_tier_table(data))                  # the table a paper should report
    cov = cm.catalog_coverage(data, clamp_bins=[(48, 54, 2.5), (108, 114, 4.0)])
    y = [cm.congestion_score(c) for c in data]      # regression target

Clearance definitions
---------------------
* :func:`min_clear_gap` (= :func:`congestion_score`): the minimum over pairs of
  the physical clear gap between insulation surfaces, taken as the larger of
  the along-gap and the out-gap per pair.  For along-adjacent neighbours of
  revision 4.0 it is exactly the generator's sampled gap.
* :func:`envelope_clearance`: the definition used for the paper's section 5.1
  on the revision 3.0 files -- the same quantity measured between 25 mm routing
  envelopes, i.e. the physical gap minus 50 mm.  On revision 4.0 data the
  physical gap already reproduces those values; keep this only for 3.0 files.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .io import DATA_VERSION, ROOT, read_payload, split_path
from .model import MEPContext, revision_for, validate_context

TIER_ORDER: List[str] = [f"C{n}" for n in range(1, 9)]
KINDS = ("pipe", "cable_tray", "duct", "conduit")
COLD = frozenset({"chilled", "domestic_cold"})
"""Services clamped over a rigid insert at the insulated diameter (cold lines);
hot and bare lines are clamped on the bare pipe."""
LEGACY_ENVELOPE_MM = 25.0      # routing envelope of data revision 3.0

ClampBin = Tuple[float, float, float]          # (lo_mm, hi_mm, capacity_kN)
CountSpec = Union[None, int, Tuple[Optional[int], Optional[int]]]


def load(split: str = "benchmark", version: str = DATA_VERSION, root: str = ROOT) -> List[dict]:
    """Contexts of a released split as plain dicts."""
    return read_payload(split_path(split, root, version))["contexts"]


def validate(ctx: dict, version: str = DATA_VERSION) -> None:
    """Run the full generator-side validator on a context dict (raises on failure)."""
    validate_context(MEPContext.from_dict(ctx, revision_for(version)))


# --------------------------------------------------------------------------- #
# Geometry on dicts (physical: bare size + insulation)                         #
# --------------------------------------------------------------------------- #

def _along(e: dict, surface_kind: str) -> float:
    return e["width_mm"] if surface_kind == "ceiling" else e["height_mm"]


def _normal(e: dict, surface_kind: str) -> float:
    return e["height_mm"] if surface_kind == "ceiling" else e["width_mm"]


def _span(e: dict, surface_kind: str) -> float:
    return _along(e, surface_kind) + 2.0 * e["insulation_mm"]


def _depth(e: dict, surface_kind: str) -> float:
    return _normal(e, surface_kind) + 2.0 * e["insulation_mm"]


def _pairs(ctx: dict):
    els, sk = ctx["elements"], ctx["surface"]["kind"]
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            yield els[i], els[j], sk


def min_clear_gap(ctx: dict) -> Optional[float]:
    """Minimum pairwise physical clear gap between insulation surfaces (mm);
    lower = more congested.  None for single-element contexts (no pairs)."""
    if len(ctx["elements"]) < 2:
        return None
    best = float("inf")
    for a, b, sk in _pairs(ctx):
        da = abs(a["along_mm"] - b["along_mm"]) - (_span(a, sk) + _span(b, sk)) / 2
        do = abs(a["out_mm"] - b["out_mm"]) - (_depth(a, sk) + _depth(b, sk)) / 2
        best = min(best, max(da, do))
    return best


congestion_score = min_clear_gap


def envelope_clearance(ctx: dict, envelope_mm: float = LEGACY_ENVELOPE_MM) -> Optional[float]:
    """Revision 3.0 definition (paper section 5.1): minimum pairwise clearance
    between routing envelopes of ``envelope_mm`` per side along the surface."""
    if len(ctx["elements"]) < 2:
        return None
    best = float("inf")
    for a, b, sk in _pairs(ctx):
        da = abs(a["along_mm"] - b["along_mm"]) - (_span(a, sk) + _span(b, sk)) / 2 - 2.0 * envelope_mm
        do = abs(a["out_mm"] - b["out_mm"]) - (_depth(a, sk) + _depth(b, sk)) / 2
        best = min(best, max(da, do))
    return best


def neighbour_gaps(ctx: dict, kind: str = "insulation") -> List[float]:
    """Clear gaps between along-adjacent neighbours within each generative row.

    ``kind``: 'insulation' (between insulation surfaces: in revision 4.0 the
    generator's sampled gap), 'bare' (between bare element surfaces, the
    quantity an IFC measurement of an uninsulated model yields) or 'envelope'
    (insulation gap minus 2 x 25 mm: the sampled gap of revision 3.0).  These
    are the samples compared with the measurements in verify/compare_gaps.py.
    """
    if kind not in ("insulation", "bare", "envelope"):
        raise ValueError(f"kind must be insulation | bare | envelope, got {kind!r}")
    sk = ctx["surface"]["kind"]
    out: List[float] = []
    for lvl in sorted({e["level"] for e in ctx["elements"]}):
        row = sorted((e for e in ctx["elements"] if e["level"] == lvl), key=lambda e: e["along_mm"])
        for a, b in zip(row, row[1:]):
            bare = (b["along_mm"] - a["along_mm"]) - (_along(a, sk) + _along(b, sk)) / 2
            if kind == "bare":
                out.append(bare)
                continue
            ins = bare - a["insulation_mm"] - b["insulation_mm"]
            out.append(ins if kind == "insulation" else ins - 2.0 * LEGACY_ENVELOPE_MM)
    return out


# --------------------------------------------------------------------------- #
# Tasks                                                                        #
# --------------------------------------------------------------------------- #

def catalog_coverage(data: Iterable[dict], clamp_bins: Sequence[ClampBin]) -> Dict[str, float]:
    """Share of pipes a clamp catalog covers, per tier and overall (percent).

    ``clamp_bins`` = [(lo_mm, hi_mm, capacity_kN), ...].  The tested diameter is
    service-correct: the insulated outer diameter for cold lines (clamped over a
    rigid insert), the bare outer diameter otherwise.  Non-pipe elements are
    counted separately: a clamp catalog never covers them.
    """
    per: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    nonpipe = 0
    for c in data:
        for e in c["elements"]:
            if e["kind"] != "pipe":
                nonpipe += 1
                continue
            dia = e["width_mm"] + (2 * e["insulation_mm"] if e["service"] in COLD else 0.0)
            ok = any(lo <= dia <= hi and e["load_kN"] <= cap for lo, hi, cap in clamp_bins)
            per[c["tier"]][0] += int(ok)
            per[c["tier"]][1] += 1
    out: Dict[str, float] = {t: round(100.0 * a / b, 1) for t, (a, b) in sorted(per.items())}
    tot_ok = sum(v[0] for v in per.values())
    tot_n = sum(v[1] for v in per.values())
    out["overall"] = round(100.0 * tot_ok / tot_n, 1) if tot_n else 0.0
    out["non_pipe_elements"] = nonpipe
    return out


def kind_counts(ctx: dict) -> Dict[str, int]:
    """Per-kind element counts for one context."""
    out = {k: 0 for k in KINDS}
    for e in ctx["elements"]:
        out[e["kind"]] += 1
    return out


def kind_totals(data: Iterable[dict]) -> Dict[str, int]:
    out = {k: 0 for k in KINDS}
    for c in data:
        for e in c["elements"]:
            out[e["kind"]] += 1
    return out


def _match(value, spec: CountSpec) -> bool:
    if spec is None:
        return True
    if isinstance(spec, tuple):
        lo, hi = spec
        return (lo is None or value >= lo) and (hi is None or value <= hi)
    return value == spec


def filter_contexts(data: Iterable[dict], pipes: CountSpec = None, trays: CountSpec = None,
                    ducts: CountSpec = None, conduits: CountSpec = None,
                    elements: CountSpec = None, tier: Optional[str] = None,
                    surface: Optional[str] = None, trades: Optional[Iterable[str]] = None,
                    levels: CountSpec = None) -> List[dict]:
    """Select contexts by composition.

    Count specs (pipes/trays/ducts/conduits/elements/levels) accept an exact int
    or a ``(lo, hi)`` tuple where either bound may be None.  ``tier`` is
    'C1'..'C8', ``surface`` 'ceiling'/'wall', ``trades`` an iterable that must
    all be present.

    Examples::

        filter_contexts(data, pipes=2, trays=1)          # exactly 2 pipes + 1 tray
        filter_contexts(data, ducts=(1, None))           # at least one duct
        filter_contexts(data, pipes=(3, 5), conduits=0)  # 3-5 pipes, no conduits
        filter_contexts(data, tier="C1", surface="wall")
    """
    want = set(trades) if trades is not None else None
    out = []
    for c in data:
        k = kind_counts(c)
        if not (_match(k["pipe"], pipes) and _match(k["cable_tray"], trays)
                and _match(k["duct"], ducts) and _match(k["conduit"], conduits)
                and _match(c["n_elements"], elements) and _match(c["n_levels"], levels)):
            continue
        if tier is not None and c["tier"] != tier:
            continue
        if surface is not None and c["surface"]["kind"] != surface:
            continue
        if want is not None and not want <= {e["trade"] for e in c["elements"]}:
            continue
        out.append(c)
    return out


def tier_summary(data: Iterable[dict], legacy_envelope: bool = False) -> Dict[str, Dict[str, float]]:
    """Per-tier medians: contexts, elements, physical clear gap, total load,
    bundle width -- plus the revision 3.0 envelope clearance when requested."""
    rows: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for c in data:
        t = c["tier"]
        rows[t]["n"].append(c["n_elements"])
        g = min_clear_gap(c)
        if g is not None:
            rows[t]["gap"].append(g)
            if legacy_envelope:
                rows[t]["env"].append(envelope_clearance(c))
        rows[t]["load"].append(c["total_load_kN"])
        rows[t]["bw"].append(c["bundle_width_mm"])
    out: Dict[str, Dict[str, float]] = {}
    for t in TIER_ORDER + sorted(set(rows) - set(TIER_ORDER)):
        if t not in rows:
            continue
        m = rows[t]
        row = {"n_ctx": len(m["n"]), "elements": median(m["n"]),
               "clear_gap_mm": median(m["gap"]) if m["gap"] else None,
               "load_kN": median(m["load"]), "bundle_width_mm": median(m["bw"])}
        if legacy_envelope:
            row["envelope_clearance_mm"] = median(m["env"]) if m["env"] else None
        out[t] = row
    return out


def tier_ranges(data: Iterable[dict]) -> Dict[str, Dict[str, float]]:
    """Per-tier ranges in the layout of the paper's Table 1: levels (min-max),
    total load (min-max, median), bundle width (min-max), ceiling share (%)."""
    rows: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for c in data:
        t = c["tier"]
        rows[t]["levels"].append(c["n_levels"])
        rows[t]["load"].append(c["total_load_kN"])
        rows[t]["bw"].append(c["bundle_width_mm"])
        rows[t]["ceiling"].append(c["surface"]["kind"] == "ceiling")
    out: Dict[str, Dict[str, float]] = {}
    for t in TIER_ORDER + sorted(set(rows) - set(TIER_ORDER)):
        if t not in rows:
            continue
        m = rows[t]
        out[t] = {"n_ctx": len(m["levels"]), "levels_min": min(m["levels"]), "levels_max": max(m["levels"]),
                  "load_min": min(m["load"]), "load_max": max(m["load"]), "load_median": median(m["load"]),
                  "width_min": min(m["bw"]), "width_max": max(m["bw"]),
                  "ceiling_pct": 100.0 * sum(m["ceiling"]) / len(m["ceiling"])}
    return out


def tier_ranges_table(data: Iterable[dict]) -> str:
    r = tier_ranges(data)
    lines = [f"{'tier':<6}{'n_ctx':>6}{'levels':>8}{'load kN min-max (med)':>24}{'width mm min-max':>18}{'ceiling/wall %':>16}"]
    for t, m in r.items():
        lv = f"{m['levels_min']}-{m['levels_max']}" if m["levels_min"] != m["levels_max"] else f"{m['levels_min']}"
        lines.append(f"{t:<6}{m['n_ctx']:>6}{lv:>8}"
                     f"{m['load_min']:>10.1f}-{m['load_max']:<5.1f}({m['load_median']:.1f}){'':>2}"
                     f"{m['width_min']:>9.0f}-{m['width_max']:<8.0f}"
                     f"{m['ceiling_pct']:>9.0f}/{100 - m['ceiling_pct']:<5.0f}")
    return "\n".join(lines)


def per_tier_table(data: Iterable[dict], legacy_envelope: bool = False) -> str:
    """Per-tier medians as a fixed-width text table (the standard reporting format)."""
    s = tier_summary(data, legacy_envelope)
    head = f"{'tier':<6}{'n_ctx':>6}{'elems':>7}{'clear-gap mm':>14}"
    if legacy_envelope:
        head += f"{'env-clear mm':>14}"
    lines = [head + f"{'load kN':>9}{'width mm':>10}"]
    for t, m in s.items():
        gap = f"{m['clear_gap_mm']:>14.0f}" if m["clear_gap_mm"] is not None else f"{'-':>14}"
        line = f"{t:<6}{m['n_ctx']:>6}{m['elements']:>7.0f}{gap}"
        if legacy_envelope:
            env = m.get("envelope_clearance_mm")
            line += f"{env:>14.0f}" if env is not None else f"{'-':>14}"
        lines.append(line + f"{m['load_kN']:>9.2f}{m['bundle_width_mm']:>10.0f}")
    return "\n".join(lines)

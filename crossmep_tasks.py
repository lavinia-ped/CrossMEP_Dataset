"""CrossMEP loader and dataset-native benchmark tasks.

Usage:
    import crossmep_tasks as cm
    data = cm.load("benchmark")                  # list of context dicts
    print(cm.per_tier_table(data))               # the table a paper should report
    cov = cm.catalog_coverage(data, clamp_bins=[(48,54,2.5),(108,114,4.0)])
    y = [cm.congestion_score(c) for c in data]   # regression target

Tasks defined here let third parties produce comparable numbers without any
additional infrastructure:
  1. catalog_coverage(data, clamp_bins): share of pipes coverable by a clamp
     catalog spec, service-correct (insulated OD for cold/chilled, bare for hot).
  2. congestion_score(ctx): minimum pairwise normalized clearance (mm); the
     regression target for difficulty-prediction baselines.
  3. per_tier_table(data): per-tier medians of elements, clearance, load, width —
     the standard reporting format.
"""
from __future__ import annotations
import json, os
from collections import defaultdict
from statistics import median

_HERE = os.path.dirname(os.path.abspath(__file__))
CLEARANCE_MM = 25.0   # must match generator (published pipe-rack minimum)


def load(split: str = "benchmark", version: str = "3.0", root: str = _HERE):
    path = os.path.join(root, f"mep_contexts_v{version}_{split}.json")
    payload = json.load(open(path))
    assert payload["dataset"] == "CrossMEP"
    return payload["contexts"]


def _span(e, surface_kind):
    along = e["width_mm"] if surface_kind == "ceiling" else e["height_mm"]
    return along + 2.0 * e["insulation_mm"] + 2.0 * CLEARANCE_MM


def _depth(e, surface_kind):
    normal = e["height_mm"] if surface_kind == "ceiling" else e["width_mm"]
    return normal + 2.0 * e["insulation_mm"]


def congestion_score(ctx):
    """Minimum pairwise normalized clearance (mm). Lower = more congested.
    Returns None for single-element contexts (no pairs)."""
    if len(ctx["elements"]) < 2:
        return None
    els, sk = ctx["elements"], ctx["surface"]["kind"]
    best = float("inf")
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = els[i], els[j]
            da = abs(a["along_mm"] - b["along_mm"]) - (_span(a, sk) + _span(b, sk)) / 2
            do = abs(a["out_mm"] - b["out_mm"]) - (_depth(a, sk) + _depth(b, sk)) / 2
            best = min(best, max(da, do))
    return best


COLD = {"chilled", "domestic_cold"}

def catalog_coverage(data, clamp_bins):
    """clamp_bins: [(lo_mm, hi_mm, capacity_kN), ...].
    Returns dict: per-tier and overall coverage of pipes (service-correct
    diameter: insulated OD for cold/chilled, bare OD otherwise), plus the count
    of non-pipe elements (always uncovered unless the catalog defines them)."""
    per = defaultdict(lambda: [0, 0])
    nonpipe = 0
    for c in data:
        for e in c["elements"]:
            if e["kind"] != "pipe":
                nonpipe += 1
                continue
            dia = e["width_mm"] + (2 * e["insulation_mm"] if e["service"] in COLD else 0.0)
            ok = any(lo <= dia <= hi and e["load_kN"] <= cap for lo, hi, cap in clamp_bins)
            per[c["tier"]][0] += ok
            per[c["tier"]][1] += 1
    out = {t: round(100.0 * a / b, 1) for t, (a, b) in sorted(per.items())}
    tot = [sum(v[0] for v in per.values()), sum(v[1] for v in per.values())]
    out["overall"] = round(100.0 * tot[0] / tot[1], 1)
    out["non_pipe_elements"] = nonpipe
    return out


TIER_ORDER = [f"C{n}" for n in range(1, 9)]


def kind_counts(ctx):
    """Per-kind element counts for one context: {'pipe': 3, 'cable_tray': 1, ...}."""
    out = {"pipe": 0, "cable_tray": 0, "duct": 0, "conduit": 0}
    for e in ctx["elements"]:
        out[e["kind"]] += 1
    return out


def _match(value, spec):
    if spec is None:
        return True
    if isinstance(spec, tuple):
        lo, hi = spec
        return (lo is None or value >= lo) and (hi is None or value <= hi)
    return value == spec


def filter_contexts(data, pipes=None, trays=None, ducts=None, conduits=None,
                    elements=None, tier=None, surface=None, trades=None,
                    levels=None):
    """Select contexts by composition. Count specs (pipes/trays/ducts/conduits/
    elements/levels) accept an exact int or a (lo, hi) tuple where either bound
    may be None. `tier` is 'C1'..'C8', `surface` is 'ceiling'/'wall', `trades`
    is an iterable that must all be present.

    Examples:
        filter_contexts(data, pipes=2, trays=1)          # exactly 2 pipes + 1 tray
        filter_contexts(data, ducts=(1, None))           # at least one duct
        filter_contexts(data, pipes=(3, 5), conduits=0)  # 3-5 pipes, no conduits
        filter_contexts(data, tier="C1", surface="wall")
    """
    out = []
    for c in data:
        k = kind_counts(c)
        if not _match(k["pipe"], pipes): continue
        if not _match(k["cable_tray"], trays): continue
        if not _match(k["duct"], ducts): continue
        if not _match(k["conduit"], conduits): continue
        if not _match(c["n_elements"], elements): continue
        if not _match(c["n_levels"], levels): continue
        if tier is not None and c["tier"] != tier: continue
        if surface is not None and c["surface"]["kind"] != surface: continue
        if trades is not None:
            present = {e["trade"] for e in c["elements"]}
            if not set(trades) <= present: continue
        out.append(c)
    return out


def per_tier_table(data) -> str:
    rows = defaultdict(lambda: defaultdict(list))
    for c in data:
        t = c["tier"]
        rows[t]["n"].append(c["n_elements"])
        cs = congestion_score(c)
        if cs is not None:
            rows[t]["clr"].append(cs)
        rows[t]["load"].append(c["total_load_kN"])
        rows[t]["bw"].append(c["bundle_width_mm"])
    lines = [f"{'tier':<5} {'n_ctx':>6} {'elems':>6} {'min-clear mm':>13} {'load kN':>8} {'width mm':>9}"]
    for t in TIER_ORDER:
        if t not in rows:
            continue
        m = rows[t]
        clr = f"{median(m['clr']):>13.0f}" if m["clr"] else f"{'\u2014':>13}"
        lines.append(f"{t:<5} {len(m['n']):>6} {median(m['n']):>6.0f} "
                     f"{clr} {median(m['load']):>8.2f} {median(m['bw']):>9.0f}")
    return "\n".join(lines)


if __name__ == "__main__":
    data = load("benchmark")
    print(per_tier_table(data))
    print("\nfilter demo \u2014 exactly 2 pipes + 1 tray, ceiling:",
          len(filter_contexts(data, pipes=2, trays=1, surface="ceiling")), "contexts")
    print("filter demo \u2014 at least one duct and one conduit:",
          len(filter_contexts(data, ducts=(1, None), conduits=(1, None))), "contexts")
    print("\ncatalog coverage (released 2-bin clamp catalog):")
    print(catalog_coverage(data, [(48, 54, 2.5), (108, 114, 4.0)]))

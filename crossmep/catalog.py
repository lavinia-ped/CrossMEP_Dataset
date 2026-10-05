"""Catalog stress test: which elements can a clamp catalog attach?

This is the question behind section 5.3 of the paper, stated precisely so that
it can be reproduced, varied and given error bars (``verify/catalog_stress.py``).

Definitions
-----------
* A catalog is a set of size bins ``Bin(lo_mm, hi_mm, capacity_kN)``: a clamp
  family that fits pipes whose *attach diameter* lies in [lo, hi] and carries at
  most ``capacity_kN`` per support.
* The attach diameter of a pipe follows one of three rules: ``"service"`` (the
  paper's: the insulated outer diameter for cold lines, which are clamped over a
  rigid insert, the bare outer diameter otherwise), ``"bare"`` or ``"insulated"``.
* An element is *attachable* when it is a pipe, its attach diameter lies in a bin
  (every bin widened by ``tol_mm`` on both sides) and its load does not exceed
  that bin's capacity.  Otherwise it is missed for exactly one reason, tested in
  this order: ``not_pipe`` (a tray, duct or conduit: a pipe-clamp catalog defines
  no attachment for it), ``size`` (no bin fits the diameter) or ``load`` (a bin
  fits but is too weak).

Scope: only size and capacity are tested.  Whether a clamp can physically be
installed (clearance to neighbours, insert orientation, anchor capacity) is not
modelled, so coverage is an upper bound on installability.

Catalog-independent view
------------------------
:func:`best_windows` and :func:`demand_curve` answer the question without
reference to any particular catalog: given the distribution of attach diameters
in a dataset, what is the largest share of pipes that ``k`` clamp sizes, each
fitting a diameter window of at most ``width_mm``, could attach?  The optimum is
computed exactly (dynamic programming over the distinct diameters).

Standard library only.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from typing import Dict, Iterable, List, Mapping, NamedTuple, Optional, Sequence, Tuple

DIAMETER_RULES = ("service", "bare", "insulated")
COLD = frozenset({"chilled", "domestic_cold"})
"""Services clamped over a rigid insert at the insulated diameter (cold lines);
hot and bare lines are clamped on the bare pipe."""
REASONS = ("covered", "not_pipe", "size", "load")


class Bin(NamedTuple):
    lo_mm: float
    hi_mm: float
    capacity_kN: float


PAPER_CATALOG: Tuple[Bin, ...] = (Bin(48.0, 54.0, 2.5), Bin(108.0, 114.0, 4.0))
"""The two-size clamp catalog of the paper's section 5.3 (48-54 mm up to 2.5 kN;
108-114 mm up to 4.0 kN).  The paper describes it as the safe-to-share catalog of
the companion SSA codebase, "reflecting real configurations"; it is used here as
a deliberately small stress-test catalog, not as a manufacturer's range, and its
derivation is documented in that codebase, not in this repository."""


def as_bins(bins: Iterable[Sequence[float]]) -> Tuple[Bin, ...]:
    return tuple(b if isinstance(b, Bin) else Bin(*b) for b in bins)


def attach_diameter(e: Mapping, rule: str = "service") -> float:
    """Diameter (mm) a clamp must fit for a pipe element, rounded to 1 um."""
    if rule == "bare":
        d = e["width_mm"]
    elif rule == "insulated":
        d = e["width_mm"] + 2.0 * e["insulation_mm"]
    elif rule == "service":
        d = e["width_mm"] + (2.0 * e["insulation_mm"] if e["service"] in COLD else 0.0)
    else:
        raise ValueError(f"rule must be one of {DIAMETER_RULES}, got {rule!r}")
    return round(d, 3)


def classify(e: Mapping, bins: Iterable[Sequence[float]], rule: str = "service",
             tol_mm: float = 0.0) -> str:
    """'covered', or the single reason an element is missed: 'not_pipe', 'size' or 'load'."""
    if e["kind"] != "pipe":
        return "not_pipe"
    d = attach_diameter(e, rule)
    fitting = [b for b in as_bins(bins) if b.lo_mm - tol_mm <= d <= b.hi_mm + tol_mm]
    if not fitting:
        return "size"
    return "covered" if any(e["load_kN"] <= b.capacity_kN for b in fitting) else "load"


def summary(contexts: Iterable[Mapping], bins: Iterable[Sequence[float]], rule: str = "service",
            tol_mm: float = 0.0) -> Dict:
    """Counts of elements by outcome, overall and per tier."""
    bins = as_bins(bins)
    total: Counter = Counter()
    per_tier: Dict[str, Counter] = {}
    for c in contexts:
        t = per_tier.setdefault(c["tier"], Counter())
        for e in c["elements"]:
            r = classify(e, bins, rule, tol_mm)
            total[r] += 1
            t[r] += 1
    def pack(k: Counter) -> Dict:
        pipes = k["covered"] + k["size"] + k["load"]
        return {"elements": pipes + k["not_pipe"], "pipes": pipes, "covered": k["covered"],
                "size": k["size"], "load": k["load"], "not_pipe": k["not_pipe"],
                "pct_pipes": 100.0 * k["covered"] / pipes if pipes else 0.0}
    out = pack(total)
    out["per_tier"] = {t: pack(k) for t, k in sorted(per_tier.items())}
    return out


def demand_points(contexts: Iterable[Mapping], rule: str = "service",
                  max_capacity_kN: Optional[float] = None) -> Counter:
    """Histogram {attach diameter (mm): number of pipes}; pipes heavier than
    ``max_capacity_kN`` (if given) are excluded."""
    pts: Counter = Counter()
    for c in contexts:
        for e in c["elements"]:
            if e["kind"] == "pipe" and (max_capacity_kN is None or e["load_kN"] <= max_capacity_kN):
                pts[attach_diameter(e, rule)] += 1
    return pts


def best_windows(points: Mapping[float, int], k: int, width_mm: float) -> Tuple[int, List[Tuple[float, float]]]:
    """Maximum number of pipes attachable with ``k`` clamp sizes, each fitting a
    diameter window of at most ``width_mm`` -- exact (dynamic programming).

    Returns ``(pipes covered, [(lo, hi), ...])`` where each (lo, hi) is the
    tightest bin spanning the diameters its window covers.
    """
    if k < 0 or width_mm < 0:
        raise ValueError("k and width_mm must be >= 0")
    xs = sorted(points)
    m = len(xs)
    ws = [points[x] for x in xs]
    prefix = [0]
    for w in ws:
        prefix.append(prefix[-1] + w)
    nxt = [bisect_right(xs, x + width_mm + 1e-9) for x in xs]       # first index a window starting at xs[i] misses
    f = [[0] * (m + 1) for _ in range(k + 1)]
    take = [[False] * (m + 1) for _ in range(k + 1)]
    for t in range(1, k + 1):
        for i in range(m - 1, -1, -1):
            use = prefix[nxt[i]] - prefix[i] + f[t - 1][nxt[i]]
            skip = f[t][i + 1]
            if use >= skip:
                f[t][i], take[t][i] = use, True
            else:
                f[t][i] = skip
    windows: List[Tuple[float, float]] = []
    t, i = k, 0
    while t > 0 and i < m:
        if take[t][i]:
            windows.append((xs[i], xs[nxt[i] - 1]))
            i, t = nxt[i], t - 1
        else:
            i += 1
    return f[k][0], windows


def demand_curve(points: Mapping[float, int], width_mm: float, k_max: Optional[int] = None) -> List[Dict]:
    """Best coverage with k = 1, 2, ... clamp sizes of window width ``width_mm``,
    up to ``k_max`` sizes or full coverage, whichever comes first."""
    total = sum(points.values())
    out: List[Dict] = []
    for k in range(1, (k_max or len(points)) + 1):
        n, wins = best_windows(points, k, width_mm)
        out.append({"k": k, "pipes": n, "pct": 100.0 * n / total if total else 0.0, "windows": wins})
        if n == total:
            break
    return out

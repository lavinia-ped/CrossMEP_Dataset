"""Context generation: canonical count-stratified tiers and user-specified compositions.

Difficulty tiers
----------------
Tier Cn contains EXACTLY n elements (C1..C8).  Composition -- kinds, trades,
services, surfaces, stacking -- is marginalised within each tier so that element
count is the single controlled difficulty axis.

Design parameters vs. empirical claims
--------------------------------------
Every probability and weight in this module is a benchmark DESIGN PARAMETER: a
choice defining the curriculum, not a measurement of building stock.  Physical
constants live in :mod:`crossmep.library`; layout constants (fitted to
measurement) in :mod:`crossmep.layout`.

Frozen random stream
--------------------
Both data revisions regenerate byte-for-byte from ``generate_split``.  The order
and arguments of every ``rng`` call in this module are therefore part of the
data format; two historical quirks are preserved and marked ``# stream:`` rather
than cleaned up.  Revision 4.0 differs from 3.0 only in layout arithmetic
(:mod:`crossmep.layout`) and recorded fields, never in a draw, so the two
revisions contain the same elements in the same rows.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from . import library as lib
from .layout import VPRIORITY, arrange
from .model import (CURRENT_REVISION, Element, MEPContext, MountingSurface, Revision,
                    revision_for, validate_context)

# --------------------------------------------------------------------------- #
# Design parameters                                                            #
# --------------------------------------------------------------------------- #

TIERS: Dict[str, int] = {f"C{n}": n for n in range(1, 9)}
"""Tier name -> exact element count."""

CANONICAL_SPLITS: Dict[str, Dict[str, int]] = {
    "train": {"n": 5000, "seed": 1000},
    "val": {"n": 500, "seed": 2000},
    "test": {"n": 500, "seed": 3000},
    "benchmark": {"n": 1000, "seed": 42},
}
"""Released splits (both revisions): disjoint seeds; tiers assigned round-robin
(125 per tier in the benchmark, 625 in train)."""

SURFACE_KINDS = ("ceiling", "wall")
SURFACE_P = (0.78, 0.22)
SUBSTRATES = ("concrete_C25", "concrete_C30")
THICKNESS_CHOICES_MM = (150, 200, 200, 250, 300)      # 200 twice: modal slab

TRADE_P = (0.3, 0.3, 0.22, 0.18)                       # over lib.PIPE_TRADES
P_DOMESTIC_SECOND_PAIR = 0.4                            # second hot+cold pair in a bank
P_HEATING_SECOND_PAIR = 0.45                            # second supply+return pair
P_SPRINKLER_BRANCH = 0.35
SPRINKLER_BRANCH_DN = (25, 32, 40)
CHILLED_BANK_SIZES = (2, 3)                             # inclusive
CONDUIT_GROUP_SIZES = (2, 6)                            # inclusive; parallel banking
TRAY_GROUP_SIZES = (1, 2)                               # inclusive
P_ROUND_DUCT = 0.25                                     # else rectangular

# Group-type options while filling a tier.  With one slot left only single
# elements are admissible; otherwise banks/groups are preferred.
OPTIONS_LAST = ("single_pipe", "tray", "duct", "conduit1")
WEIGHTS_LAST = (0.55, 0.18, 0.15, 0.12)
OPTIONS_MULTI = ("pipe_bank", "tray_group", "duct", "conduit_group", "single_pipe")
WEIGHTS_MULTI = (0.46, 0.16, 0.12, 0.16, 0.10)
WALL_DUCT_FACTOR = 0.3                                  # ducts are rare on walls

MAX_CUSTOM_ELEMENTS = 12


def rows_for(n: int, surface: MountingSurface, rng: np.random.Generator) -> int:
    """Number of generative rows: 1 for a single element, 1-2 up to five
    elements, 2-3 above; walls are limited to two rows (draw first, then clamp)."""
    if n == 1:
        r = 1
    elif n <= 5:
        r = int(rng.integers(1, 3))
    else:
        r = int(rng.integers(2, 4))
    return min(r, 2) if surface.kind == "wall" else r


def stagger_for(n: int) -> float:
    """Half-normal stagger scale (mm) by element count; calibrated to the
    measured in-bundle elevation spread (VERIFICATION_LOG.md section 6)."""
    return 0.0 if n == 1 else (75.0 if n <= 5 else 120.0)


# --------------------------------------------------------------------------- #
# Samplers (each consumes rng draws in a fixed order)                          #
# --------------------------------------------------------------------------- #

def sample_surface(rng: np.random.Generator, kind: Optional[str] = None) -> MountingSurface:
    k = kind or str(rng.choice(SURFACE_KINDS, p=SURFACE_P))
    return MountingSurface(kind=k, substrate=str(rng.choice(SUBSTRATES)),
                           thickness_mm=float(rng.choice(THICKNESS_CHOICES_MM)))


def sample_tray(rng: np.random.Generator) -> Element:
    return lib.make_tray(int(rng.choice(lib.TRAY_WIDTHS_MM)))


def sample_duct(rng: np.random.Generator) -> Element:
    if rng.random() < P_ROUND_DUCT:
        return lib.make_round_duct(int(rng.choice(lib.ROUND_DUCT_D_MM)))
    w, h = lib.RECT_DUCT_SIZES_MM[int(rng.integers(0, len(lib.RECT_DUCT_SIZES_MM)))]
    return lib.make_rect_duct(w, h)


def sample_conduit_group(rng: np.random.Generator) -> List[Element]:
    """A parallel group of 2-6 conduits of one size."""
    n = int(rng.integers(CONDUIT_GROUP_SIZES[0], CONDUIT_GROUP_SIZES[1] + 1))
    od = int(rng.choice(lib.CONDUIT_OD_MM))
    return [lib.make_conduit(od) for _ in range(n)]


def sample_pipe_bank(rng: np.random.Generator, trade: str) -> List[Element]:
    """Pipes grouped the way trades run: domestic hot+cold pairs, heating
    supply+return pairs, a sprinkler main with an optional branch, chilled banks."""
    band = lib.dn_band(trade)
    if trade == "domestic":
        s = int(rng.choice(band))
        bank = [lib.make_pipe(s, "domestic_hot", trade), lib.make_pipe(s, "domestic_cold", trade)]
        if rng.random() < P_DOMESTIC_SECOND_PAIR:
            s2 = int(rng.choice(band))
            bank += [lib.make_pipe(s2, "domestic_hot", trade), lib.make_pipe(s2, "domestic_cold", trade)]
        return bank
    if trade == "heating":
        s = int(rng.choice(band))
        bank = [lib.make_pipe(s, "heating", trade), lib.make_pipe(s, "heating", trade)]
        if rng.random() < P_HEATING_SECOND_PAIR:
            s2 = int(rng.choice(band))
            bank += [lib.make_pipe(s2, "heating", trade), lib.make_pipe(s2, "heating", trade)]
        return bank
    if trade == "sprinkler":
        bank = [lib.make_pipe(int(rng.choice(band)), "sprinkler", trade)]
        if rng.random() < P_SPRINKLER_BRANCH:
            bank.append(lib.make_pipe(int(rng.choice(SPRINKLER_BRANCH_DN)), "sprinkler", trade))
        return bank
    n = int(rng.integers(CHILLED_BANK_SIZES[0], CHILLED_BANK_SIZES[1] + 1))
    return [lib.make_pipe(int(rng.choice(band)), "chilled", trade) for _ in range(n)]


def sample_single_pipe(rng: np.random.Generator) -> Element:
    trade = str(rng.choice(lib.PIPE_TRADES, p=TRADE_P))
    # stream: the hot/cold draw is made for EVERY trade (v3.0 evaluated it inside
    # a dict literal); it is only used when the trade is domestic.
    hot_or_cold = str(rng.choice(("domestic_hot", "domestic_cold")))
    service = hot_or_cold if trade == "domestic" else trade
    return lib.make_pipe(int(rng.choice(lib.dn_band(trade))), service, trade)


def _finish(groups: List[Tuple[int, List[Element]]], n: int, surface: MountingSurface,
            rng: np.random.Generator, tier: str, context_id: str,
            revision: Revision) -> MEPContext:
    n_rows = rows_for(n, surface, rng)
    els = arrange(groups, n_rows, surface, stagger_for(n), rng=rng,
                  envelope_mm=revision.layout_envelope_mm)
    ctx = MEPContext(tuple(els), surface, tier, context_id, revision)
    validate_context(ctx)
    return ctx


# --------------------------------------------------------------------------- #
# Canonical tiers                                                              #
# --------------------------------------------------------------------------- #

def generate_context(rng: np.random.Generator, tier: str = "C3", context_id: str = "",
                     revision: Revision = CURRENT_REVISION) -> MEPContext:
    """One context of tier ``tier`` (exactly ``TIERS[tier]`` elements), validated."""
    n_target = TIERS[tier]
    surface = sample_surface(rng)
    groups: List[Tuple[int, List[Element]]] = []
    remaining = n_target
    while remaining > 0:
        if remaining == 1:
            opts, w = OPTIONS_LAST, np.array(WEIGHTS_LAST)
        else:
            opts, w = OPTIONS_MULTI, np.array(WEIGHTS_MULTI)
        if surface.kind == "wall":
            w[opts.index("duct")] *= WALL_DUCT_FACTOR
        choice = str(rng.choice(opts, p=w / w.sum()))
        if choice == "pipe_bank":
            trade = str(rng.choice(lib.PIPE_TRADES, p=TRADE_P))
            bank = sample_pipe_bank(rng, trade)[:remaining]    # trimming = a lone supply line
            groups.append((VPRIORITY["pipe"], bank))
            remaining -= len(bank)
        elif choice == "single_pipe":
            groups.append((VPRIORITY["pipe"], [sample_single_pipe(rng)]))
            remaining -= 1
        elif choice in ("tray", "tray_group"):
            k = 1 if choice == "tray" else int(min(remaining, rng.integers(TRAY_GROUP_SIZES[0], TRAY_GROUP_SIZES[1] + 1)))
            groups.append((VPRIORITY["cable_tray"], [sample_tray(rng) for _ in range(k)]))
            remaining -= k
        elif choice == "duct":
            groups.append((VPRIORITY["duct"], [sample_duct(rng)]))
            remaining -= 1
        else:                                                   # conduit1 / conduit_group
            # stream: a full group is sampled and then trimmed, also for conduit1.
            group = sample_conduit_group(rng)[:remaining]
            groups.append((VPRIORITY["conduit"], group))
            remaining -= len(group)
    return _finish(groups, n_target, surface, rng, tier, context_id, revision)


def generate_dataset(n: int, seed: int = 0, tier: Optional[str] = None,
                     id_prefix: str = "mep",
                     revision: Union[Revision, str] = CURRENT_REVISION) -> List[MEPContext]:
    """``n`` validated contexts from ``seed``; tiers round-robin C1..C8 unless fixed."""
    rev = revision_for(revision) if isinstance(revision, str) else revision
    rng = np.random.default_rng(seed)
    names = list(TIERS)
    return [generate_context(rng, tier or names[i % len(names)], context_id=f"{id_prefix}_{i}",
                             revision=rev)
            for i in range(n)]


def generate_split(name: str, version: str = CURRENT_REVISION.version) -> List[MEPContext]:
    """Regenerate a canonical split (train | val | test | benchmark) of a data revision."""
    spec = CANONICAL_SPLITS[name]
    return generate_dataset(spec["n"], seed=spec["seed"], revision=revision_for(version))


# --------------------------------------------------------------------------- #
# Custom composition (the constructive API)                                    #
# --------------------------------------------------------------------------- #

CountSpec = Union[int, Tuple[int, int]]


def _resolve_count(name: str, spec: CountSpec, rng: np.random.Generator) -> int:
    """A count spec is an exact int or an inclusive (lo, hi) tuple."""
    if isinstance(spec, bool) or spec is None:
        raise ValueError(f"{name}: expected int or (lo, hi) tuple, got {spec!r}")
    if isinstance(spec, int):
        if spec < 0:
            raise ValueError(f"{name}: count must be >= 0, got {spec}")
        return spec
    if isinstance(spec, tuple) and len(spec) == 2:
        lo, hi = spec
        if not (isinstance(lo, int) and isinstance(hi, int) and 0 <= lo <= hi):
            raise ValueError(f"{name}: range must be (lo, hi) ints with 0 <= lo <= hi, got {spec!r}")
        return int(rng.integers(lo, hi + 1))
    raise ValueError(f"{name}: expected int or (lo, hi) tuple, got {spec!r}")


def generate_custom(n: int, *, pipes: CountSpec = 0, trays: CountSpec = 0,
                    ducts: CountSpec = 0, conduits: CountSpec = 0,
                    surface: Optional[str] = None, trades: Optional[Sequence[str]] = None,
                    seed: int = 0) -> List[MEPContext]:
    """``n`` contexts with a USER-SPECIFIED composition (current data revision).

    Each count accepts an exact int or an inclusive ``(lo, hi)`` tuple resolved
    independently per context.  ``surface`` fixes 'ceiling' or 'wall' (default:
    the natural 78/22 mix).  ``trades`` restricts pipe trades to a subset of
    ``library.PIPE_TRADES``.

    Custom scenes reuse the verified element library and the same layout rules
    as the canonical tiers (fitted gaps, published clearance floor, calibrated
    stagger, wall drip rule), so they are construction-VALID by the same rules.
    They are tagged ``tier='custom'`` because realism VERIFICATION attaches to
    the natural distribution, not to arbitrary compositions.

    Examples::

        generate_custom(100, pipes=3, trays=1)
        generate_custom(50, pipes=(2, 4), conduits=(2, 6), surface="ceiling")
        generate_custom(20, pipes=2, trades=["chilled"], seed=7)
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError(f"n: must be a positive int, got {n!r}")
    if surface not in (None, "ceiling", "wall"):
        raise ValueError(f"surface: must be 'ceiling', 'wall', or None, got {surface!r}")
    allowed = list(lib.PIPE_TRADES)
    if trades is not None:
        trades = list(trades)
        bad = set(trades) - set(allowed)
        if bad or not trades:
            raise ValueError(f"trades: must be a non-empty subset of {allowed}, got {trades!r}")
    rng = np.random.default_rng(seed)
    pool = trades or allowed
    trade_w = np.array([TRADE_P[allowed.index(t)] for t in pool])
    out: List[MEPContext] = []
    for i in range(n):
        n_p, n_t, n_d, n_c = (_resolve_count("pipes", pipes, rng), _resolve_count("trays", trays, rng),
                              _resolve_count("ducts", ducts, rng), _resolve_count("conduits", conduits, rng))
        total = n_p + n_t + n_d + n_c
        if total == 0:
            raise ValueError("composition resolves to zero elements; request at least one")
        if total > MAX_CUSTOM_ELEMENTS:
            raise ValueError(f"composition resolves to {total} elements; maximum is {MAX_CUSTOM_ELEMENTS}")
        surf = sample_surface(rng, kind=surface)
        groups: List[Tuple[int, List[Element]]] = []
        remaining = n_p                                         # pipes -> realistic banks
        while remaining > 0:
            t = str(rng.choice(pool, p=trade_w / trade_w.sum()))
            bank = sample_pipe_bank(rng, t)[:remaining]
            groups.append((VPRIORITY["pipe"], bank))
            remaining -= len(bank)
        left = n_t                                              # trays, 1-2 per group
        while left > 0:
            k = int(min(left, rng.integers(TRAY_GROUP_SIZES[0], TRAY_GROUP_SIZES[1] + 1)))
            groups.append((VPRIORITY["cable_tray"], [sample_tray(rng) for _ in range(k)]))
            left -= k
        for _ in range(n_d):                                    # ducts, one per group
            groups.append((VPRIORITY["duct"], [sample_duct(rng)]))
        left = n_c                                              # conduits, groups of <= 6
        while left > 0:
            k = int(min(left, rng.integers(CONDUIT_GROUP_SIZES[0], CONDUIT_GROUP_SIZES[1] + 1))) if left > 1 else 1
            groups.append((VPRIORITY["conduit"], sample_conduit_group(rng)[:k]))
            left -= k
        out.append(_finish(groups, total, surf, rng, "custom", f"custom_{i}", CURRENT_REVISION))
    return out

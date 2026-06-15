"""
MEP context sampler — realistic synthetic MEP scenes, no assembly information.

A context describes ONLY the MEP scene a support will later be designed for:
  - the elements carried (pipes, cable trays, ducts), their sizes / services /
    loads, and how they sit in the cross-section: an offset ALONG the mounting
    surface and a standoff OUT from it (so services can stack), and
  - the surface (ceiling or wall, substrate, thickness).
Nothing about the support itself (no channel, rods, attachments, topology).

SURFACE-AWARE GEOMETRY
The cross-section's screen axes are building-horizontal (x) and building-vertical
(y) for both surfaces; what changes is the surface position and which axis the
elements spread along:
  - ceiling: spread ALONG = horizontal, OUT = downward (depth below slab)
  - wall:    spread ALONG = vertical (elevation), OUT = horizontal (projection)
So an element's size ALONG the surface is its width on a ceiling but its height
on a wall (the section rotates). _span()/_depth() encode that; the same arrange
and validation serve both. Ducts are rare on walls (reduced frequency).

HEIGHTS / STAGGER
Services stack in rows (bulky nearest the surface: ducts, then trays, then
pipes). Rows are no longer a rigid grid: elements within a row are staggered on
the OUT axis (amplitude grows with tier), so heights vary the way coordinated
MEP actually does. Stagger is safe because elements in a row are already cleared
ALONG the surface.

DIFFICULTY TIERS (scene complexity, not "hard to support"):
  T1 intro          2-3 elements, 1 trade, pipes, 1 row,  no stagger, DN15-32
  T2 two services   3-5 elements, 1-2 trades, pipes(+tray), 1 row,    DN15-50
  T3 mixed+stacked  4-6 elements, 2-3 trades, pipes+tray+duct, 1-2 rows, stagger, DN15-80
  T4 congested      5-9 elements, 2-3 trades, pipes+tray+duct, 2-3 rows, stagger, DN15-100

Every context passes validate_context(): pairwise clearance (cleared ALONG or
OUT), and each row centered. This is a NEW module; the repo's single-pipe
ssa.core.mep_context is untouched.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Dict, List, Tuple

import numpy as np

# --------------------------------------------------------------------------- #
# Reference data (synthetic, public-grounded)                                  #
# --------------------------------------------------------------------------- #

DN_OD_MM = {15: 21.3, 20: 26.9, 25: 33.7, 32: 42.4, 40: 48.3, 50: 60.3,
            65: 76.1, 80: 88.9, 100: 114.3}
# Per-support load = water-filled sch40 weight (kg/m) x typical support span,
# rounded. Spans per ASME B31.1 Table 121.5-style practice (~2.0 m at DN15
# rising to ~4.0 m at DN100); weights from standard sch40 + water content.
# e.g. DN50: 7.6 kg/m x 3.0 m = 0.22 kN; DN100: 24.3 kg/m x 4.3 m = 1.0 kN.
DN_LOAD_KN = {15: 0.03, 20: 0.04, 25: 0.06, 32: 0.08, 40: 0.10, 50: 0.21,
              65: 0.30, 80: 0.49, 100: 0.88}
# Steel mass: EN 10255:2004 medium-series walls x 7,850 kg/m3 + water at bore.
# Spans use ONLY published ASME B31.1 Table 121.5 water-service points
# (NPS1=2.1 m, NPS2=3.0 m, NPS3=3.7 m, NPS4=4.3 m) via a floor rule: each DN
# takes the span of the largest published size not exceeding it. No
# interpolated values.
# Derivation (fully sourced): steel mass from EN 10255:2004 medium-series wall
# thickness (2.6-4.5 mm by DN) x 7,850 kg/m3 + water content at internal bore;
# per-support load = mass/m x span from ASME B31.1 Table 121.5 water-service
# spans as widely republished (NPS1=2.1 m, NPS2=3.0 m, NPS3=3.7 m, NPS4=4.3 m;
# DN32/40=2.7 m and DN65=3.4 m interpolated, flagged in VERIFICATION_LOG.md).
def insulation_mm(service: str, dn: int) -> float:
    """Code-grounded insulation schedule, per side, as a function of service AND size.

    Heated lines (heating, domestic hot): German GEG Anlage 8 '100%' rule,
    thickness keyed to pipe diameter -- 20 mm up to ~DN20, 30 mm to ~DN32,
    then thickness ~= DN, capped at 100 mm.
    Chilled water (condensation control): 30 mm up to DN40, 50 mm above
    (common employer's-requirement schedule, e.g. UNOG standard).
    Cold potable and sprinkler: bare (thin anti-sweat sleeves excluded)."""
    if service in ("heating", "domestic_hot"):
        if dn <= 20: return 20.0
        if dn <= 32: return 30.0
        return float(min(dn, 100))
    if service == "chilled":
        return 30.0 if dn <= 40 else 50.0
    return 0.0

TRAY_WIDTHS = [150, 225, 300, 450, 600]
TRAY_HEIGHT_MM = 60.0
# Loaded tray per support: ~75 kg/m2 cable loading (mid NEMA/IEC class) + tray
# self-weight, x ~2 m support spacing.
TRAY_LOAD_KN = {150: 0.54, 225: 0.81, 300: 1.08, 450: 1.62, 600: 2.16}
# Design-for-full basis: supports carry the tray at rated fill, not today's
# cables. Published datum: a 300 mm tray full of power cables ~50 kg/m
# (NEC 392 40%-fill basis) + steel tray self-weight ~5 kg/m at 300 mm,
# both scaled linearly with width; span 2.0 m (typical tray support spacing).
# Design-for-full basis: supports carry the tray at rated fill, not today's
# cables. Published datum: a 300 mm tray full of power cables ~50 kg/m
# (NEC 392 40%-fill basis) + steel tray self-weight ~5 kg/m at 300 mm,
# both scaled linearly with width; span 2.0 m (typical tray support spacing).

DUCT_SIZES = [(250, 200), (400, 250), (500, 400), (800, 400), (1000, 500)]
ROUND_DUCT_D = [160, 200, 250, 315, 400, 500]      # subset of EN 1506:2007 nominal sizes
ROUND_DUCT_LOAD_KN = {160: 0.056, 200: 0.070, 250: 0.087, 315: 0.110,
                      400: 0.139, 500: 0.174}
# Spiral duct plain-sheet mass: pi x D x 0.6 mm gauge (manufacturer gauge tables
# for D<=500) x 7,850 kg/m3, span 2.4 m; excludes fittings.
# Spiral duct plain-sheet mass: pi x D x 0.6 mm gauge (manufacturer gauge tables
# for D<=500) x 7,850 kg/m3, span 2.4 m; excludes fittings.
# Walraven 'Air Duct Dimensions and Weights' datasheet (non-insulated, incl.
# flange/bracing allowance): 400x250=11.7, 600x300~19.3, 800x400=24.5,
# 1000x500=30.6 kg/m; 250x150=6.1 extrapolated one grid step below the table;
# span 2.4 m (8-ft hanger-spacing practice).
# Electrical conduits: IEC 61386-1 metric trade sizes (specified by OUTER
# diameter below 80 mm); routed in
# parallel groups, uninsulated, light loads (conduit + cable fill x ~2 m spacing).
CONDUIT_OD = [20, 25, 32, 40, 50]
CONDUIT_LOAD_KN = {20: 0.021, 25: 0.029, 32: 0.044, 40: 0.063, 50: 0.092}
# Steel conduit (wall 1.5 mm per BS 4568 / IEC 61386-21 class range 1.2-1.6 mm)
# x 7,850 kg/m3 + IEC 40%-of-bore cable fill at 4,167 kg/m3 effective cable
# density (back-derived from the published 50 kg/m full 300 mm tray datum);
# span 2.0 m.
DUCT_LOAD_KN = {250: 0.16, 400: 0.28, 500: 0.38, 800: 0.58, 1000: 0.72}
# Verbatim Walraven 'Air Duct Dimensions and Weights' table cells (non-insulated,
# incl. flange/bracing): 250x200=6.9, 400x250=11.7, 500x400=16.2, 800x400=24.5,
# 1000x500=30.6 kg/m; span 2.4 m (8-ft hanger practice). No extrapolated cells.

CLEARANCE_MM = 25.0          # published pipe-rack minimum clearance         # routing clearance per side, along the surface
GAP_INTRA_MM = 25.0         # published pipe-rack minimum clear gap
GAP_INTER_MM = 25.0          # same published floor; larger separation arises
                             # from the measurement-fitted gap distribution         # clear gap between trades on a row
ROW_VGAP_MM = 120.0         # clearance between stacked rows (out direction)
TOP_OFFSET_MM = 90.0        # standoff of the first row from the surface

_VPRIORITY = {"duct": 0, "cable_tray": 1, "conduit": 1, "pipe": 2}   # lower sits nearer surface
SUBSTRATES = ["concrete_C25", "concrete_C30"]

TIERS: Dict[str, dict] = {f"C{n}": dict(n=n) for n in range(1, 9)}
# v3 stratification: tier = EXACT element count (C1..C8). Composition (kinds,
# trades, services, surfaces) is marginalized within each tier so that count is
# the single difficulty axis. Composition weights below are benchmark DESIGN
# PARAMETERS (choices defining the curriculum, not empirical claims).
_DN_ALL = [15, 20, 25, 32, 40, 50, 65, 80, 100]


@dataclass(frozen=True)
class Element:
    kind: str                  # "pipe" | "cable_tray" | "duct"
    service: str               # precise service ("domestic_hot", "heating", "tray",
                               # "duct", ...): with insulation, determines the
                               # attachment method downstream (bare-pipe clamp vs
                               # rigid insert at insulation diameter on cold lines)
    trade: str
    shape: str                 # "round" | "rect"
    width_mm: float            # building-horizontal size
    height_mm: float           # building-vertical size
    insulation_mm: float
    load_kN: float
    label: str
    position_along_mm: float = 0.0   # offset along the surface (centered on 0)
    position_out_mm: float = 0.0     # standoff from the surface (row center + stagger)
    level: int = 0                   # GENERATIVE METADATA: row index of the tiered
                                     # layout pattern (0 = nearest surface). Not a
                                     # physical invariant -- consumers must rely on
                                     # the continuous (along, out) coordinates and
                                     # pairwise clearance, never on rows.


@dataclass(frozen=True)
class MountingSurface:
    kind: str                  # "ceiling" | "wall"
    substrate: str
    thickness_mm: float


def _span(e: Element, surface: MountingSurface) -> float:
    """Element extent ALONG the surface (incl. insulation + routing clearance)."""
    along = e.width_mm if surface.kind == "ceiling" else e.height_mm
    return along + 2.0 * e.insulation_mm + 2.0 * CLEARANCE_MM


def _depth(e: Element, surface: MountingSurface) -> float:
    """Element extent OUT from the surface (incl. insulation)."""
    normal = e.height_mm if surface.kind == "ceiling" else e.width_mm
    return normal + 2.0 * e.insulation_mm


@dataclass(frozen=True)
class MEPContext:
    elements: Tuple[Element, ...]
    surface: MountingSurface
    tier: str = ""
    context_id: str = ""

    @property
    def total_load_kN(self) -> float:
        return sum(e.load_kN for e in self.elements)

    @property
    def n_levels(self) -> int:
        return len({e.level for e in self.elements})

    @property
    def bundle_width_mm(self) -> float:
        lo = min(e.position_along_mm - _span(e, self.surface) / 2 for e in self.elements)
        hi = max(e.position_along_mm + _span(e, self.surface) / 2 for e in self.elements)
        return hi - lo

    def to_dict(self) -> dict:
        return {
            "context_id": self.context_id, "tier": self.tier,
            "surface": {"kind": self.surface.kind, "substrate": self.surface.substrate,
                        "thickness_mm": self.surface.thickness_mm},
            "n_elements": len(self.elements), "n_levels": self.n_levels,
            "total_load_kN": round(self.total_load_kN, 2),
            "bundle_width_mm": round(self.bundle_width_mm, 1),
            "elements": [
                {"kind": e.kind, "service": e.service, "trade": e.trade, "shape": e.shape, "label": e.label,
                 "width_mm": e.width_mm, "height_mm": e.height_mm,
                 "insulation_mm": e.insulation_mm, "load_kN": e.load_kN, "level": e.level,
                 "along_mm": round(e.position_along_mm, 1), "out_mm": round(e.position_out_mm, 1)}
                for e in self.elements
            ],
        }


# --------------------------------------------------------------------------- #
# Element + bank constructors                                                  #
# --------------------------------------------------------------------------- #

def _pipe(dn: int, service: str, trade: str) -> Element:
    insul = insulation_mm(service, dn)
    return Element("pipe", service, trade, "round", DN_OD_MM[dn], DN_OD_MM[dn],
                   insul, DN_LOAD_KN[dn], f"DN{dn}")


def _tray(rng) -> Element:
    w = int(rng.choice(TRAY_WIDTHS))
    return Element("cable_tray", "tray", "electrical", "rect", float(w), TRAY_HEIGHT_MM,
                   0.0, TRAY_LOAD_KN[w], f"{w} tray")


def _duct(rng) -> Element:
    if rng.random() < 0.25:                       # round spiral duct variant
        dd = int(rng.choice(ROUND_DUCT_D))
        return Element("duct", "duct", "ventilation", "round", float(dd), float(dd),
                       0.0, ROUND_DUCT_LOAD_KN[dd], f"\u00D8{dd} duct")
    # Duct thermal insulation is excluded: no verified thickness source; see
    # DATASHEET limitations.
    w, h = DUCT_SIZES[int(rng.integers(0, len(DUCT_SIZES)))]
    return Element("duct", "duct", "ventilation", "rect", float(w), float(h),
                   0.0, DUCT_LOAD_KN[w], f"{w}x{h} duct")


def _conduit_group(rng) -> List[Element]:
    n = int(rng.integers(2, 7))                   # parallel groups of 2-6
    od = int(rng.choice(CONDUIT_OD))
    return [Element("conduit", "conduit", "electrical", "round", float(od), float(od),
                    0.0, CONDUIT_LOAD_KN[od], f"\u00D8{od} conduit") for _ in range(n)]


def _pipe_bank(rng, trade: str, pool: List[int]) -> List[Element]:
    band = {"domestic": [s for s in pool if s <= 32],
            "sprinkler": [s for s in pool if 25 <= s <= 100],
            "heating": [s for s in pool if 20 <= s <= 65],
            "chilled": [s for s in pool if 25 <= s <= 100]}.get(trade) or pool
    band = band or pool
    if trade == "domestic":
        s = int(rng.choice(band))
        b = [_pipe(s, "domestic_hot", "domestic"), _pipe(s, "domestic_cold", "domestic")]
        if rng.random() < 0.4:
            s2 = int(rng.choice(band))
            b += [_pipe(s2, "domestic_hot", "domestic"), _pipe(s2, "domestic_cold", "domestic")]
        return b
    if trade == "heating":
        s = int(rng.choice(band))
        b = [_pipe(s, "heating", "heating"), _pipe(s, "heating", "heating")]
        if rng.random() < 0.45:
            s2 = int(rng.choice(band))
            b += [_pipe(s2, "heating", "heating"), _pipe(s2, "heating", "heating")]
        return b
    if trade == "sprinkler":
        # fire mains run uninsulated steel, typically one main + sometimes a branch
        band = [s for s in pool if 25 <= s <= 100] or pool
        b = [_pipe(int(rng.choice(band)), "sprinkler", "sprinkler")]
        if rng.random() < 0.35:
            b.append(_pipe(int(rng.choice([25, 32, 40])), "sprinkler", "sprinkler"))
        return b
    n = int(rng.integers(2, 4))
    return [_pipe(int(rng.choice(band)), "chilled", "chilled") for _ in range(n)]


# --------------------------------------------------------------------------- #
# Arrangement: stack groups into rows, lay each row out ALONG, stagger OUT      #
# --------------------------------------------------------------------------- #

def _arrange(groups: List[Tuple[int, List[Element]]], n_rows: int,
             surface: MountingSurface, stagger: float, rng=None) -> List[Element]:
    # Gap realism (measured on the open Duplex Apartment IFC model): clear gaps
    # between parallel runs are irregular -- p25 ~55 mm to p75 ~480 mm -- not a
    # fixed module. We keep GAP_*_MM as the floor and jitter upward.
    # Gaps: sampled from a lognormal FITTED to measured Duplex clear gaps above
    # the 25 mm clearance floor (n=73, <600 mm; mu=5.018, sigma=0.848, KS p=0.53).
    # GAP_*_MM stays the hard floor; samples capped at 500 mm.
    GAP_MU, GAP_SIGMA = 5.018, 0.848
    def _gap(base):
        if rng is None:
            return base
        draw = float(np.exp(rng.normal(GAP_MU, GAP_SIGMA)))
        return float(min(max(base, draw), 500.0))
    groups = sorted(groups, key=lambda g: g[0])
    n_rows = max(1, min(n_rows, len(groups)))
    rows: List[List[Element]] = [[] for _ in range(n_rows)]
    for i, (_prio, els) in enumerate(groups):
        rows[min(i, n_rows - 1)].extend(els)

    out: List[Element] = []
    cursor = TOP_OFFSET_MM
    for ri, row in enumerate(rows):
        # Walls: keep electrical containment ABOVE wet services within the row
        # (smaller along = higher elevation) -- coordination practice avoids
        # routing water-bearing pipes directly above trays/conduits (drip risk).
        if surface.kind == "wall":
            row = sorted(row, key=lambda e: 0 if e.kind in ("cable_tray", "conduit") else 1)
        # lay out ALONG the surface (wider gap when trade changes)
        a = []
        x = 0.0
        for j, e in enumerate(row):
            sp = _span(e, surface)
            if j == 0:
                x = sp / 2.0
            else:
                gap = _gap(GAP_INTER_MM) if row[j - 1].trade != e.trade else _gap(GAP_INTRA_MM)
                x = a[-1] + _span(row[j - 1], surface) / 2.0 + gap + sp / 2.0
            a.append(x)
        mid = (a[0] - _span(row[0], surface) / 2.0 + a[-1] + _span(row[-1], surface) / 2.0) / 2.0
        # stagger OUT within the row: half-normal offsets calibrated to the
        # measured in-bundle elevation spread (Duplex: median 79 mm, p75 282).
        if rng is None or stagger <= 0:
            douts = [stagger * (j % 2) for j in range(len(row))]
        else:
            douts = [float(min(abs(rng.normal(0.0, stagger)), 2.5 * stagger))
                     for _ in range(len(row))]
        near = [douts[j] - _depth(row[j], surface) / 2.0 for j in range(len(row))]
        far = [douts[j] + _depth(row[j], surface) / 2.0 for j in range(len(row))]
        shift = cursor - min(near)
        for j, e in enumerate(row):
            out.append(replace(e, position_along_mm=round(a[j] - mid, 1),
                               position_out_mm=round(douts[j] + shift, 1), level=ri))
        cursor = max(far) + shift + ROW_VGAP_MM
    return out


def _single_pipe(rng) -> Element:
    trade = str(rng.choice(["domestic", "heating", "chilled", "sprinkler"],
                           p=[0.3, 0.3, 0.22, 0.18]))
    band = {"domestic": [s for s in _DN_ALL if s <= 32],
            "sprinkler": [s for s in _DN_ALL if 25 <= s <= 100],
            "heating": [s for s in _DN_ALL if 20 <= s <= 65],
            "chilled": [s for s in _DN_ALL if 25 <= s <= 100]}[trade]
    svc = {"domestic": str(rng.choice(["domestic_hot", "domestic_cold"])),
           "heating": "heating", "chilled": "chilled", "sprinkler": "sprinkler"}[trade]
    return _pipe(int(rng.choice(band)), svc, trade)


def generate_context(rng, tier: str = "C3", context_id: str = "") -> MEPContext:
    n_target = TIERS[tier]["n"]
    surface = MountingSurface(
        kind=str(rng.choice(["ceiling", "wall"], p=[0.78, 0.22])),
        substrate=str(rng.choice(SUBSTRATES)),
        thickness_mm=float(rng.choice([150, 200, 200, 250, 300])))
    groups: List[Tuple[int, List[Element]]] = []
    remaining = n_target
    while remaining > 0:
        if remaining == 1:
            opts = ["single_pipe", "tray", "duct", "conduit1"]
            w = np.array([0.55, 0.18, 0.15, 0.12])
        else:
            opts = ["pipe_bank", "tray_group", "duct", "conduit_group", "single_pipe"]
            w = np.array([0.46, 0.16, 0.12, 0.16, 0.10])
        if surface.kind == "wall" and "duct" in opts:
            w[opts.index("duct")] *= 0.3      # ducts rare on walls
        ch = str(rng.choice(opts, p=w / w.sum()))
        if ch == "pipe_bank":
            trade = str(rng.choice(["domestic", "heating", "chilled", "sprinkler"],
                                   p=[0.3, 0.3, 0.22, 0.18]))
            b = _pipe_bank(rng, trade, _DN_ALL)[:remaining]   # trimming = a lone
            groups.append((_VPRIORITY["pipe"], b))            # supply line, realistic
            remaining -= len(b)
        elif ch == "single_pipe":
            groups.append((_VPRIORITY["pipe"], [_single_pipe(rng)])); remaining -= 1
        elif ch in ("tray", "tray_group"):
            k = 1 if ch == "tray" else int(min(remaining, rng.integers(1, 3)))
            groups.append((_VPRIORITY["cable_tray"], [_tray(rng) for _ in range(k)]))
            remaining -= k
        elif ch == "duct":
            groups.append((_VPRIORITY["duct"], [_duct(rng)])); remaining -= 1
        else:
            g = _conduit_group(rng)[:remaining]
            groups.append((_VPRIORITY["conduit"], g)); remaining -= len(g)
    if n_target == 1:
        n_rows = 1
    elif n_target <= 5:
        n_rows = int(rng.integers(1, 3))
    else:
        n_rows = int(rng.integers(2, 4))
    if surface.kind == "wall":
        n_rows = min(n_rows, 2)
    # stagger uses the measurement-calibrated half-normal scales
    stagger = 0.0 if n_target == 1 else (75.0 if n_target <= 5 else 120.0)
    els = _arrange(groups, n_rows, surface, stagger, rng=rng)
    return MEPContext(tuple(els), surface, tier, context_id)


def generate_dataset(n: int, seed: int = 0, tier: str = None) -> List[MEPContext]:
    rng = np.random.default_rng(seed)
    tiers = list(TIERS.keys())
    return [generate_context(rng, tier or tiers[i % len(tiers)], context_id=f"mep_{i}")
            for i in range(n)]


# --------------------------------------------------------------------------- #
# Custom generation -- user-specified composition (the constructive API)       #
# --------------------------------------------------------------------------- #

_MAX_CUSTOM_ELEMENTS = 12


def _resolve_count(name, spec, rng):
    """A count spec is an exact int or a (lo, hi) tuple; resolve to one int."""
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


def generate_custom(n: int, *, pipes=0, trays=0, ducts=0, conduits=0,
                    surface: str = None, trades: List[str] = None,
                    seed: int = 0) -> List[MEPContext]:
    """Generate n contexts with a USER-SPECIFIED composition.

    Each count accepts an exact int or a (lo, hi) tuple resolved independently
    per context. `surface` fixes 'ceiling' or 'wall' (default: natural 78/22
    mix). `trades` restricts pipe trades to a subset of
    {domestic, heating, chilled, sprinkler}.

    Custom scenes reuse the verified element library and the same physics as
    the canonical tiers -- fitted gap distribution, published clearance floor,
    calibrated stagger, wall drip rule -- so they are construction-VALID by the
    same rules. They are tagged tier='custom' because realism VERIFICATION
    attaches to the natural distribution, not to arbitrary compositions.

    Examples:
        generate_custom(100, pipes=3, trays=1)
        generate_custom(50, pipes=(2, 4), conduits=(2, 6), surface="ceiling")
        generate_custom(20, pipes=2, trades=["chilled"], seed=7)
    """
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"n: must be a positive int, got {n!r}")
    if surface not in (None, "ceiling", "wall"):
        raise ValueError(f"surface: must be 'ceiling', 'wall', or None, got {surface!r}")
    allowed = ["domestic", "heating", "chilled", "sprinkler"]
    if trades is not None:
        bad = set(trades) - set(allowed)
        if bad or not trades:
            raise ValueError(f"trades: must be a non-empty subset of {allowed}, got {trades!r}")
    rng = np.random.default_rng(seed)
    out: List[MEPContext] = []
    for i in range(n):
        np_, nt, nd, nc = (_resolve_count("pipes", pipes, rng),
                           _resolve_count("trays", trays, rng),
                           _resolve_count("ducts", ducts, rng),
                           _resolve_count("conduits", conduits, rng))
        total = np_ + nt + nd + nc
        if total == 0:
            raise ValueError("composition resolves to zero elements; request at least one")
        if total > _MAX_CUSTOM_ELEMENTS:
            raise ValueError(f"composition resolves to {total} elements; "
                             f"maximum is {_MAX_CUSTOM_ELEMENTS}")
        surf = MountingSurface(
            kind=surface or str(rng.choice(["ceiling", "wall"], p=[0.78, 0.22])),
            substrate=str(rng.choice(SUBSTRATES)),
            thickness_mm=float(rng.choice([150, 200, 200, 250, 300])))
        groups: List[Tuple[int, List[Element]]] = []
        remaining = np_                                   # pipes -> realistic banks
        pool = trades or allowed
        pw = np.array([{"domestic": 0.3, "heating": 0.3,
                        "chilled": 0.22, "sprinkler": 0.18}[t] for t in pool])
        while remaining > 0:
            t = str(rng.choice(pool, p=pw / pw.sum()))
            b = _pipe_bank(rng, t, _DN_ALL)[:remaining]   # trim = lone supply line
            groups.append((_VPRIORITY["pipe"], b))
            remaining -= len(b)
        if nt:                                            # trays, 1-2 per group
            left = nt
            while left > 0:
                k = int(min(left, rng.integers(1, 3)))
                groups.append((_VPRIORITY["cable_tray"], [_tray(rng) for _ in range(k)]))
                left -= k
        for _ in range(nd):                               # ducts, one per group
            groups.append((_VPRIORITY["duct"], [_duct(rng)]))
        if nc:                                            # conduits, groups of <=6
            left = nc
            while left > 0:
                k = int(min(left, rng.integers(2, 7))) if left > 1 else 1
                groups.append((_VPRIORITY["conduit"],
                               _conduit_group(rng)[:k] if k > 1
                               else _conduit_group(rng)[:1]))
                left -= k
        if total == 1:
            n_rows = 1
        elif total <= 5:
            n_rows = int(rng.integers(1, 3))
        else:
            n_rows = int(rng.integers(2, 4))
        if surf.kind == "wall":
            n_rows = min(n_rows, 2)
        stagger = 0.0 if total == 1 else (75.0 if total <= 5 else 120.0)
        els = _arrange(groups, n_rows, surf, stagger, rng=rng)
        ctx = MEPContext(tuple(els), surf, "custom", f"custom_{i}")
        validate_context(ctx)
        out.append(ctx)
    return out


# --------------------------------------------------------------------------- #
# Validation — pairwise clearance (cleared ALONG or OUT), rows centered         #
# --------------------------------------------------------------------------- #

def validate_context(ctx: MEPContext) -> None:
    EPS = 0.5
    surf = ctx.surface
    els = ctx.elements
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = els[i], els[j]
            da = abs(a.position_along_mm - b.position_along_mm)
            do = abs(a.position_out_mm - b.position_out_mm)
            need_a = _span(a, surf) / 2 + _span(b, surf) / 2
            need_o = _depth(a, surf) / 2 + _depth(b, surf) / 2
            assert da >= need_a - EPS or do >= need_o - EPS, \
                f"{ctx.context_id}: {a.label} and {b.label} overlap"
    by_level: Dict[int, List[Element]] = {}
    for e in els:
        by_level.setdefault(e.level, []).append(e)
    for lvl, row in by_level.items():
        lo = min(e.position_along_mm - _span(e, surf) / 2 for e in row)
        hi = max(e.position_along_mm + _span(e, surf) / 2 for e in row)
        assert abs(lo + hi) <= 1.5, f"{ctx.context_id}: row {lvl} not centered"


# --------------------------------------------------------------------------- #
# SVG — MEP scene only; correct ceiling vs wall orientation                     #
# --------------------------------------------------------------------------- #

_TRADE_COLOR = {"domestic": "#2f6fed", "heating": "#e8833a", "chilled": "#0f9d8c",
                "sprinkler": "#d2434a",
                "electrical": "#7c5cd6", "ventilation": "#52606d"}
_HATCH = ('<defs><pattern id="hatch" width="7" height="7" patternTransform="rotate(45)" '
          'patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="7" '
          'stroke="#cbd2d9" stroke-width="1.4"/></pattern></defs>')


def _draw_element(e, x0, y0, s, out):
    col = _TRADE_COLOR.get(e.trade, "#5a6b78")
    if e.shape == "round":
        r = max(3.0, e.width_mm * s / 2.0)
        if e.insulation_mm > 0:
            out.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="{r + max(2.0, e.insulation_mm*s):.1f}" '
                       f'fill="none" stroke="{col}" stroke-width="1" stroke-dasharray="2 2" opacity="0.55"/>')
        out.append(f'<circle cx="{x0:.1f}" cy="{y0:.1f}" r="{r:.1f}" fill="none" stroke="{col}" stroke-width="2.3"/>')
        out.append(f'<text x="{x0:.1f}" y="{y0 + r + 11:.1f}" font-size="8.5" fill="{col}" '
                   f'text-anchor="middle" font-family="ui-monospace,monospace">{e.label}</text>')
    else:
        wpx, hpx = e.width_mm * s, e.height_mm * s
        fill = "#f4f1fa" if e.kind == "cable_tray" else "#eef1f4"
        out.append(f'<rect x="{x0-wpx/2:.1f}" y="{y0-hpx/2:.1f}" width="{wpx:.1f}" height="{hpx:.1f}" '
                   f'rx="3" fill="{fill}" stroke="{col}" stroke-width="2.3"/>')
        out.append(f'<text x="{x0:.1f}" y="{y0+3:.1f}" font-size="8.5" fill="{col}" '
                   f'text-anchor="middle" font-family="ui-monospace,monospace">{e.label}</text>')


def _svg_ceiling(ctx: MEPContext, w: int) -> str:
    a_lo = min(e.position_along_mm - e.width_mm / 2 for e in ctx.elements)
    a_hi = max(e.position_along_mm + e.width_mm / 2 for e in ctx.elements)
    out_hi = max(e.position_out_mm + e.height_mm / 2 for e in ctx.elements)
    aspan = max(a_hi - a_lo, 1.0)
    padx, surf_y, topgap, padb = 22, 22, 8, 30
    s = min((w - 2 * padx) / aspan, 300.0 / max(out_hi, 1.0))
    h = int(surf_y + topgap + out_hi * s + padb)
    cx, amid = w / 2.0, (a_lo + a_hi) / 2.0
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" width="100%">', _HATCH]
    o.append(f'<rect x="0" y="0" width="{w}" height="{surf_y}" fill="url(#hatch)"/>')
    o.append(f'<line x1="0" y1="{surf_y}" x2="{w}" y2="{surf_y}" stroke="#52606d" stroke-width="2.5"/>')
    o.append(f'<text x="8" y="15" font-size="9.5" fill="#5a6b78" font-family="ui-monospace,monospace">'
             f'{ctx.surface.kind} · {ctx.surface.substrate}</text>')
    for e in ctx.elements:
        _draw_element(e, cx + (e.position_along_mm - amid) * s, surf_y + topgap + e.position_out_mm * s, s, o)
    o.append(f'<text x="{cx:.1f}" y="{h-6:.1f}" font-size="9.5" fill="#5a6b78" text-anchor="middle" '
             f'font-family="ui-monospace,monospace">{len(ctx.elements)} elements · '
             f'{ctx.total_load_kN:.2f} kN · {ctx.n_levels} level(s)</text>')
    o.append("</svg>")
    return "".join(o)


def _svg_wall(ctx: MEPContext, w: int) -> str:
    a_lo = min(e.position_along_mm - e.height_mm / 2 for e in ctx.elements)
    a_hi = max(e.position_along_mm + e.height_mm / 2 for e in ctx.elements)
    out_hi = max(e.position_out_mm + e.width_mm / 2 for e in ctx.elements)
    aspan = max(a_hi - a_lo, 1.0)
    wall_w, padx, topgap, padb = 16, 14, 20, 28
    s = min((w - wall_w - 2 * padx) / max(out_hi, 1.0), 300.0 / aspan)
    h = int(topgap + aspan * s + padb)
    o = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" width="100%">', _HATCH]
    o.append(f'<rect x="0" y="0" width="{wall_w}" height="{h}" fill="url(#hatch)"/>')
    o.append(f'<line x1="{wall_w}" y1="0" x2="{wall_w}" y2="{h}" stroke="#52606d" stroke-width="2.5"/>')
    o.append(f'<text x="{wall_w+6}" y="14" font-size="9.5" fill="#5a6b78" font-family="ui-monospace,monospace">'
             f'{ctx.surface.kind} · {ctx.surface.substrate}</text>')
    for e in ctx.elements:
        _draw_element(e, wall_w + padx + e.position_out_mm * s, topgap + (e.position_along_mm - a_lo) * s, s, o)
    o.append(f'<text x="{w/2:.1f}" y="{h-6:.1f}" font-size="9.5" fill="#5a6b78" text-anchor="middle" '
             f'font-family="ui-monospace,monospace">{len(ctx.elements)} elements · '
             f'{ctx.total_load_kN:.2f} kN · {ctx.n_levels} level(s)</text>')
    o.append("</svg>")
    return "".join(o)


def _context_svg(ctx: MEPContext, w: int = 360) -> str:
    return _svg_wall(ctx, w) if ctx.surface.kind == "wall" else _svg_ceiling(ctx, w)


def render_preview_html(contexts: List[MEPContext], path: str) -> str:
    cards = []
    for ctx in contexts:
        trades = ", ".join(sorted({e.trade for e in ctx.elements}))
        cards.append(
            f'<div class="card"><div class="hd"><span class="id">{ctx.context_id} · {ctx.tier}</span>'
            f'<span class="tr">{trades}</span></div>{_context_svg(ctx)}</div>')
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
            "*{box-sizing:border-box}body{margin:0;padding:20px;background:#f7f9fb;"
            "font-family:ui-sans-serif,system-ui,sans-serif;color:#1f2933}"
            "h1{font-size:16px;margin:0 0 4px}p{color:#5a6b78;font-size:13px;margin:0 0 16px}"
            ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;align-items:start}"
            ".card{background:#fff;border:1px solid #d4dce2;border-radius:12px;padding:10px}"
            ".hd{display:flex;justify-content:space-between;margin-bottom:4px}"
            ".id{font-family:ui-monospace,monospace;font-size:12px;color:#5a6b78}"
            ".tr{font-size:11px;color:#3e4c59}</style></head><body>"
            "<h1>Synthetic MEP contexts</h1><p>Cross-section of the MEP scene only — surface "
            "hatched (top = ceiling, left = wall), round = pipe, rectangles = duct / cable tray, "
            "staggered by height. No support assembly.</p>"
            f"<div class='grid'>{''.join(cards)}</div></body></html>")
    with open(path, "w") as f:
        f.write(html)
    return path


_GALLERY_TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>MEP context dataset</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:22px;background:#f7f9fb;color:#1f2933;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
h1{font-size:18px;margin:0 0 2px}#stat{color:#5a6b78;font-size:13px;font-family:ui-monospace,Menlo,Consolas,monospace;margin:0 0 16px}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#5a6b78;margin:0 0 10px}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px;margin:0 0 22px}
.chart{background:#fff;border:1px solid #d4dce2;border-radius:12px;padding:12px 14px}
.brow{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:11.5px}
.lab{width:74px;color:#3e4c59;font-family:ui-monospace,monospace;text-align:right;flex:none}
.track{flex:1;background:#eef3f6;border-radius:4px;height:14px;overflow:hidden}
.fill{display:block;height:100%;background:#0f9d8c;border-radius:4px}
.val{width:34px;color:#5a6b78;font-family:ui-monospace,monospace;flex:none}
.fbar{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:0 0 8px}
.fbar .g{font-size:11px;color:#5a6b78;margin:0 4px 0 10px;text-transform:uppercase;letter-spacing:.05em}
.fbar .g:first-child{margin-left:0}
.fbar button{font:inherit;font-size:12px;padding:4px 10px;border:1px solid #d4dce2;background:#fff;border-radius:999px;cursor:pointer;color:#1f2933}
.fbar button.active{background:#16222e;color:#fff;border-color:#16222e}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;align-items:start}
.card{background:#fff;border:1px solid #d4dce2;border-radius:12px;padding:10px}
.hd{display:flex;justify-content:space-between;margin-bottom:2px}
.id{font-family:ui-monospace,monospace;font-size:12px;color:#5a6b78}.tr{font-size:11px;color:#3e4c59}
</style></head><body>
<h1>Synthetic MEP context dataset</h1>
<p id="stat"></p>
<div class="charts">
  <div class="chart"><h2>difficulty tier</h2><div id="c-tier"></div></div>
  <div class="chart"><h2>elements per context</h2><div id="c-n"></div></div>
  <div class="chart"><h2>element kinds (all)</h2><div id="c-kind"></div></div>
  <div class="chart"><h2>levels (rows)</h2><div id="c-lev"></div></div>
  <div class="chart"><h2>contexts containing trade</h2><div id="c-tr"></div></div>
  <div class="chart"><h2>total load per context (kN)</h2><div id="c-load"></div></div>
</div>
<div class="fbar">
  <span class="g">tier</span>
  <button data-g="tier" data-v="all" class="active">all</button>
  <button data-g="tier" data-v="C1">C1</button><button data-g="tier" data-v="C2">C2</button>
  <button data-g="tier" data-v="C3">C3</button><button data-g="tier" data-v="C4">C4</button>
  <button data-g="tier" data-v="C5">C5</button><button data-g="tier" data-v="C6">C6</button>
  <button data-g="tier" data-v="C7">C7</button><button data-g="tier" data-v="C8">C8</button>
  <span class="g">kind</span>
  <button data-g="kind" data-v="all" class="active">all</button>
  <button data-g="kind" data-v="pipe">pipe</button>
  <button data-g="kind" data-v="cable_tray">tray</button>
  <button data-g="kind" data-v="duct">duct</button>
  <button data-g="kind" data-v="conduit">conduit</button>
  <span class="g">trade</span>
  <button data-g="trade" data-v="all" class="active">all</button>
  <button data-g="trade" data-v="domestic">dom</button><button data-g="trade" data-v="heating">heat</button>
  <button data-g="trade" data-v="chilled">chill</button><button data-g="trade" data-v="sprinkler">sprk</button><button data-g="trade" data-v="electrical">elec</button>
  <button data-g="trade" data-v="ventilation">vent</button>
  <span class="g">surface</span>
  <button data-g="su" data-v="all" class="active">all</button>
  <button data-g="su" data-v="ceiling">ceiling</button><button data-g="su" data-v="wall">wall</button>
</div>
<div class="grid" id="grid">/*CARDS*/</div>
<script>
var DATA = /*DATA*/;
var F = {tier:"all", kind:"all", trade:"all", su:"all"};
var grid = document.getElementById('grid');
var cards = Array.prototype.slice.call(grid.children);
function matchN(n,f){ return f==="all" || (f==="7+" ? n>=7 : String(n)===f); }
function cnt(d,pred){ var k=0,i; for(i=0;i<d.length;i++){ if(pred(d[i])) k++; } return k; }
function bars(id,pairs){
  var max=1,i; for(i=0;i<pairs.length;i++){ if(pairs[i][1]>max) max=pairs[i][1]; }
  var h=""; for(i=0;i<pairs.length;i++){
    h+='<div class="brow"><span class="lab">'+pairs[i][0]+'</span><span class="track"><span class="fill" style="width:'+(100*pairs[i][1]/max)+'%"></span></span><span class="val">'+pairs[i][1]+'</span></div>';
  }
  document.getElementById(id).innerHTML=h;
}
function draw(d){
  bars('c-tier',['C1','C2','C3','C4','C5','C6','C7','C8'].map(function(t){return [t,cnt(d,function(x){return x.tier===t;})];}));
  bars('c-n',['1','2','3','4','5','6','7','8'].map(function(v){return [v,cnt(d,function(x){return matchN(x.n,v);})];}));
  var km={pipe:0,cable_tray:0,duct:0,conduit:0},i,j;
  for(i=0;i<d.length;i++){ for(j=0;j<d[i].kinds_all.length;j++){ km[d[i].kinds_all[j]]++; } }
  bars('c-kind',[['pipe',km.pipe],['tray',km.cable_tray],['duct',km.duct],['conduit',km.conduit]]);
  bars('c-lev',[1,2,3].map(function(L){return [L+' row'+(L>1?'s':''),cnt(d,function(x){return x.levels===L;})];}));
  bars('c-tr',['domestic','heating','chilled','sprinkler','electrical','ventilation'].map(function(t){return [t.slice(0,5),cnt(d,function(x){return x.trades.indexOf(t)>=0;})];}));
  var bk=[['0-0.5',0,0.5],['0.5-1',0.5,1],['1-2',1,2],['2-4',2,4],['4+',4,1e9]];
  bars('c-load',bk.map(function(b){return [b[0],cnt(d,function(x){return x.load>=b[1]&&x.load<b[2];})];}));
  var ne=0,k; for(k=0;k<d.length;k++){ ne+=d[k].n; }
  document.getElementById('stat').textContent=d.length+' contexts  \\u00b7  '+ne+' elements  \\u00b7  '+(d.length?(ne/d.length).toFixed(1):0)+' /context';
}
function ok(d){ return (F.tier==="all"||d.tier===F.tier)&&(F.kind==="all"||d.kinds.indexOf(F.kind)>=0)&&(F.trade==="all"||d.trades.indexOf(F.trade)>=0)&&(F.su==="all"||d.su===F.su); }
function apply(){
  var i; for(i=0;i<cards.length;i++){ var c=cards[i];
    var show=(F.tier==="all"||c.getAttribute('data-tier')===F.tier)
      &&(F.kind==="all"||c.getAttribute('data-kinds').split(' ').indexOf(F.kind)>=0)
      &&(F.trade==="all"||c.getAttribute('data-trades').split(' ').indexOf(F.trade)>=0)
      &&(F.su==="all"||c.getAttribute('data-su')===F.su);
    c.style.display=show?'':'none';
  }
  var vis=[]; for(i=0;i<DATA.length;i++){ if(ok(DATA[i])) vis.push(DATA[i]); }
  draw(vis);
}
var btns=document.querySelectorAll('.fbar button'),bi;
for(bi=0;bi<btns.length;bi++){ (function(b){
  b.onclick=function(){
    var g=b.getAttribute('data-g'); F[g]=b.getAttribute('data-v');
    var same=document.querySelectorAll('.fbar button[data-g="'+g+'"]'),k;
    for(k=0;k<same.length;k++){ same[k].className=(same[k]===b)?'active':''; }
    apply();
  };
})(btns[bi]); }
apply();
</script></body></html>"""


def render_gallery_html(contexts: List[MEPContext], path: str) -> str:
    cards, data = [], []
    for ctx in contexts:
        trades = sorted({e.trade for e in ctx.elements})
        kinds = sorted({e.kind for e in ctx.elements})
        cards.append(
            f'<div class="card" data-tier="{ctx.tier}" data-trades="{" ".join(trades)}" '
            f'data-kinds="{" ".join(kinds)}" data-su="{ctx.surface.kind}">'
            f'<div class="hd"><span class="id">{ctx.context_id} · {ctx.tier}</span>'
            f'<span class="tr">{", ".join(trades)}</span></div>{_context_svg(ctx)}</div>')
        data.append({"tier": ctx.tier, "n": len(ctx.elements), "levels": ctx.n_levels,
                     "trades": trades, "kinds": kinds, "kinds_all": [e.kind for e in ctx.elements],
                     "su": ctx.surface.kind, "load": round(ctx.total_load_kN, 2)})
    html = (_GALLERY_TEMPLATE.replace("/*CARDS*/", "".join(cards))
            .replace("/*DATA*/", json.dumps(data)))
    with open(path, "w") as f:
        f.write(html)
    return path


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Sample tiered MEP contexts (no assembly info).")
    ap.add_argument("--n", type=int, default=320)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tier", type=str, default=None, choices=list(TIERS.keys()),
                    help="fix a single tier; default = even mix of C1..C8")
    ap.add_argument("--pipes", type=int, default=None, help="custom mode: exact pipe count")
    ap.add_argument("--trays", type=int, default=None, help="custom mode: exact tray count")
    ap.add_argument("--ducts", type=int, default=None, help="custom mode: exact duct count")
    ap.add_argument("--conduits", type=int, default=None, help="custom mode: exact conduit count")
    ap.add_argument("--surface", type=str, default=None, choices=["ceiling", "wall"])
    ap.add_argument("--json", type=str, default="mep_contexts.json")
    ap.add_argument("--preview", type=str, default="mep_contexts_preview.html")
    ap.add_argument("--gallery", type=str, default="mep_contexts_gallery.html")
    args = ap.parse_args()

    custom = any(v is not None for v in (args.pipes, args.trays, args.ducts, args.conduits))
    if custom:
        data = generate_custom(args.n, pipes=args.pipes or 0, trays=args.trays or 0,
                               ducts=args.ducts or 0, conduits=args.conduits or 0,
                               surface=args.surface, seed=args.seed)
    else:
        data = generate_dataset(args.n, seed=args.seed, tier=args.tier)
    for ctx in data:
        validate_context(ctx)
    payload = {
        "dataset": "CrossMEP",
        "version": "3.1",
        "generator": "mep_context_sampler.py",
        "seed": args.seed,
        "n_contexts": len(data),
        "tier_policy": ("custom composition" if custom else (args.tier or "even mix C1-C8")),
        "units": "mm, kN",
        "schema_notes": {
            "scope": "MEP scene only; intentionally contains no support-assembly information",
            "level": "generative row index of the tiered layout pattern; not a physical invariant",
            "load_kN": "per-support-point operating load at typical support spacing",
            "service": "precise service; with insulation_mm, determines attachment method (bare clamp vs rigid insert)",
            "coordinates": "along = offset along the surface (centered per row); out = standoff from the surface, positive away",
        },
        "contexts": [c.to_dict() for c in data],
    }
    with open(args.json, "w") as f:
        json.dump(payload, f, indent=2)
    render_preview_html(data[:12], args.preview)
    render_gallery_html(data, args.gallery)
    print(f"generated {len(data)} valid MEP contexts (tiers: {args.tier or 'C1-C8 mix'})")
    print(f"  -> {args.json}")
    print(f"  -> {args.preview}")
    print(f"  -> {args.gallery}")

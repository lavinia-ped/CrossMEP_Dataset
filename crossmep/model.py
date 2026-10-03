"""Data model: elements, mounting surface, context, geometry helpers, validation.

Coordinate convention (surface-aware)
-------------------------------------
Every context is a 2-D cross-section perpendicular to the run direction at one
support location.  Element positions are expressed in a *surface frame*:

* ``along_mm`` -- offset ALONG the mounting surface (building-horizontal on a
  ceiling, building-vertical on a wall), centred on 0 within each row;
* ``out_mm``   -- standoff OUT from the surface, positive away from it (downward
  from a ceiling, horizontal projection from a wall).

``width_mm`` x ``height_mm`` are building-horizontal x building-vertical, so an
element's extent ALONG the surface is its width on a ceiling but its height on a
wall (the section rotates).  :func:`span_along` and :func:`depth_out` encode that
mapping once; generation, validation and the metrics all go through them.

Clearance envelope
------------------
:func:`span_along` includes the insulation (both sides) plus a routing clearance
of ``CLEARANCE_MM`` per side.  Two elements are cleared when they are separated
ALONG by their combined half-spans, or OUT by their combined half-depths plus the
same clearance on each side.  Consequently the clear gap between the insulation
envelopes of along-adjacent neighbours is the sampled gap plus 2 * CLEARANCE_MM
(see :mod:`crossmep.layout` and VERIFICATION_LOG.md section 6).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

CLEARANCE_MM = 25.0
"""Routing clearance per element side, along the surface (mm).
Source: published pipe-rack minimum clearance -- VERIFICATION_LOG.md section 6."""

KINDS: Tuple[str, ...] = ("pipe", "cable_tray", "duct", "conduit")
SHAPES: Tuple[str, ...] = ("round", "rect")
SURFACE_KINDS: Tuple[str, ...] = ("ceiling", "wall")
TRADES: Tuple[str, ...] = ("domestic", "heating", "chilled", "sprinkler",
                           "electrical", "ventilation")
SERVICES: Tuple[str, ...] = ("domestic_hot", "domestic_cold", "heating", "chilled",
                             "sprinkler", "tray", "duct", "conduit")
WET_TRADES = frozenset({"domestic", "heating", "chilled", "sprinkler"})
ELECTRICAL_KINDS = frozenset({"cable_tray", "conduit"})


class ContextValidationError(ValueError):
    """Raised by :func:`validate_context` when a context violates an invariant."""


@dataclass(frozen=True)
class Element:
    """One MEP element in the cross-section.  Units: mm, kN."""
    kind: str            # pipe | cable_tray | duct | conduit
    service: str         # precise service (domestic_hot, heating, chilled, tray, ...).
                         # With insulation_mm it determines the attachment method a
                         # downstream catalog admits (bare clamp vs rigid insert).
    trade: str           # domestic | heating | chilled | sprinkler | electrical | ventilation
    shape: str           # round | rect
    width_mm: float      # building-horizontal size, bare (no insulation)
    height_mm: float     # building-vertical size, bare
    insulation_mm: float  # per side
    load_kN: float       # per support point at the typical span (library.py)
    label: str
    position_along_mm: float = 0.0
    position_out_mm: float = 0.0
    level: int = 0       # GENERATIVE METADATA: row index of the tiered layout
                         # pattern (0 = nearest the surface).  Not a physical
                         # invariant; consumers must use the continuous
                         # coordinates and pairwise clearance, never rows.

    def to_dict(self) -> dict:
        return {"kind": self.kind, "service": self.service, "trade": self.trade,
                "shape": self.shape, "label": self.label,
                "width_mm": self.width_mm, "height_mm": self.height_mm,
                "insulation_mm": self.insulation_mm, "load_kN": self.load_kN,
                "level": self.level,
                "along_mm": round(self.position_along_mm, 1),
                "out_mm": round(self.position_out_mm, 1)}

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        return cls(kind=d["kind"], service=d["service"], trade=d["trade"],
                   shape=d["shape"], width_mm=float(d["width_mm"]),
                   height_mm=float(d["height_mm"]),
                   insulation_mm=float(d["insulation_mm"]), load_kN=float(d["load_kN"]),
                   label=d["label"], position_along_mm=float(d["along_mm"]),
                   position_out_mm=float(d["out_mm"]), level=int(d["level"]))


@dataclass(frozen=True)
class MountingSurface:
    kind: str            # ceiling | wall
    substrate: str       # e.g. concrete_C25
    thickness_mm: float

    def to_dict(self) -> dict:
        return {"kind": self.kind, "substrate": self.substrate,
                "thickness_mm": self.thickness_mm}

    @classmethod
    def from_dict(cls, d: dict) -> "MountingSurface":
        return cls(kind=d["kind"], substrate=d["substrate"],
                   thickness_mm=float(d["thickness_mm"]))


def span_along(e: Element, surface: MountingSurface) -> float:
    """Extent ALONG the surface: bare size + insulation + routing clearance, both sides."""
    along = e.width_mm if surface.kind == "ceiling" else e.height_mm
    return along + 2.0 * e.insulation_mm + 2.0 * CLEARANCE_MM


def depth_out(e: Element, surface: MountingSurface) -> float:
    """Extent OUT from the surface: bare size + insulation, both sides (no clearance)."""
    normal = e.height_mm if surface.kind == "ceiling" else e.width_mm
    return normal + 2.0 * e.insulation_mm


@dataclass(frozen=True)
class MEPContext:
    """A cross-section: the elements a support must carry and the surface it mounts to.

    Deliberately contains no support-assembly information.
    """
    elements: Tuple[Element, ...]
    surface: MountingSurface
    tier: str = ""
    context_id: str = ""

    @property
    def total_load_kN(self) -> float:
        # math.fsum is exactly rounded, so the value does not depend on the
        # Python version (3.12 changed sum() to compensated summation, which
        # flips round(x, 2) at .xx5 boundaries for 28 of the 7,000 released
        # contexts if plain sum() is used on 3.11).
        return math.fsum(e.load_kN for e in self.elements)

    @property
    def n_levels(self) -> int:
        return len({e.level for e in self.elements})

    @property
    def bundle_width_mm(self) -> float:
        """Overall extent along the surface, clearance envelopes included."""
        lo = min(e.position_along_mm - span_along(e, self.surface) / 2 for e in self.elements)
        hi = max(e.position_along_mm + span_along(e, self.surface) / 2 for e in self.elements)
        return hi - lo

    def kind_counts(self) -> Dict[str, int]:
        out = {k: 0 for k in KINDS}
        for e in self.elements:
            out[e.kind] += 1
        return out

    def to_dict(self) -> dict:
        # Key order is part of the release format (files are regenerated
        # byte-for-byte); do not reorder.
        return {
            "context_id": self.context_id, "tier": self.tier,
            "surface": self.surface.to_dict(),
            "n_elements": len(self.elements), "n_levels": self.n_levels,
            "total_load_kN": round(self.total_load_kN, 2),
            "bundle_width_mm": round(self.bundle_width_mm, 1),
            "elements": [e.to_dict() for e in self.elements],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MEPContext":
        return cls(elements=tuple(Element.from_dict(e) for e in d["elements"]),
                   surface=MountingSurface.from_dict(d["surface"]),
                   tier=d.get("tier", ""), context_id=d.get("context_id", ""))


# --------------------------------------------------------------------------- #
# Validation                                                                   #
# --------------------------------------------------------------------------- #

POSITION_EPS_MM = 0.5     # positions are stored to 0.1 mm; allow rounding slack
CENTERING_TOL_MM = 1.5    # per-row centring tolerance (two rounded endpoints)


def pair_clearance(a: Element, b: Element, surface: MountingSurface) -> float:
    """Signed clearance between two elements (mm): the larger of the along-excess
    (beyond combined half-spans, clearance envelopes included) and the out-excess
    (beyond combined half-depths).  Negative means the envelopes overlap in both
    directions.  This is the quantity ``crossmep.tasks.congestion_score`` minimises."""
    da = abs(a.position_along_mm - b.position_along_mm) - (span_along(a, surface) + span_along(b, surface)) / 2
    do = abs(a.position_out_mm - b.position_out_mm) - (depth_out(a, surface) + depth_out(b, surface)) / 2
    return max(da, do)


def validate_context(ctx: MEPContext) -> None:
    """Raise :class:`ContextValidationError` unless every invariant holds.

    Invariants (all released contexts satisfy them; tests enforce them over many
    unseen seeds):

    1. field domains: kinds, shapes, trades, services, surface kind; positive
       sizes and loads; non-negative insulation; standoff ``out_mm`` > 0;
    2. pairwise clearance: every pair is separated ALONG by at least the combined
       half-spans (insulation + CLEARANCE_MM per side), or OUT by at least the
       combined half-depths plus CLEARANCE_MM per side;
    3. per-row centring: each generative row is centred on along = 0.
    """
    cid = ctx.context_id or "<context>"
    if not ctx.elements:
        raise ContextValidationError(f"{cid}: no elements")
    if ctx.surface.kind not in SURFACE_KINDS:
        raise ContextValidationError(f"{cid}: bad surface kind {ctx.surface.kind!r}")
    if not ctx.surface.thickness_mm > 0:
        raise ContextValidationError(f"{cid}: surface thickness must be > 0")
    for e in ctx.elements:
        if e.kind not in KINDS or e.shape not in SHAPES or e.trade not in TRADES \
                or e.service not in SERVICES:
            raise ContextValidationError(f"{cid}: {e.label}: bad kind/shape/trade/service")
        if not (e.width_mm > 0 and e.height_mm > 0 and e.load_kN > 0):
            raise ContextValidationError(f"{cid}: {e.label}: size and load must be > 0")
        if e.insulation_mm < 0 or e.level < 0:
            raise ContextValidationError(f"{cid}: {e.label}: negative insulation or level")
        if e.shape == "round" and e.width_mm != e.height_mm:
            raise ContextValidationError(f"{cid}: {e.label}: round element must be square")
        if not e.position_out_mm > 0:
            raise ContextValidationError(f"{cid}: {e.label}: standoff must be > 0")
    surf = ctx.surface
    els = ctx.elements
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = els[i], els[j]
            da = abs(a.position_along_mm - b.position_along_mm)
            do = abs(a.position_out_mm - b.position_out_mm)
            need_a = (span_along(a, surf) + span_along(b, surf)) / 2
            need_o = (depth_out(a, surf) + depth_out(b, surf)) / 2 + 2.0 * CLEARANCE_MM
            if not (da >= need_a - POSITION_EPS_MM or do >= need_o - POSITION_EPS_MM):
                raise ContextValidationError(
                    f"{cid}: {a.label} and {b.label} are not cleared "
                    f"(along {da:.1f} < {need_a:.1f} and out {do:.1f} < {need_o:.1f})")
    by_level: Dict[int, List[Element]] = {}
    for e in els:
        by_level.setdefault(e.level, []).append(e)
    for lvl, row in by_level.items():
        lo = min(e.position_along_mm - span_along(e, surf) / 2 for e in row)
        hi = max(e.position_along_mm + span_along(e, surf) / 2 for e in row)
        if abs(lo + hi) > CENTERING_TOL_MM:
            raise ContextValidationError(f"{cid}: row {lvl} not centred (lo {lo:.1f}, hi {hi:.1f})")


def is_valid(ctx: MEPContext) -> bool:
    try:
        validate_context(ctx)
    except ContextValidationError:
        return False
    return True

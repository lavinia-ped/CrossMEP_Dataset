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

Physical extents and the clearance rule
---------------------------------------
:func:`span_along` and :func:`depth_out` are *physical*: bare size plus
insulation on both sides, nothing else.  Two elements are cleared when their
insulation surfaces are at least ``MIN_CLEAR_GAP_MM`` apart ALONG the surface
or OUT from it.  That is the only clearance rule; the layout engine samples the
along-gap from a distribution fitted to measurement (see :mod:`crossmep.layout`).

Data revisions
--------------
Data revision **4.0** records exactly this geometry.  Revision **3.0** (the files
the CIB W78 2026 paper was released with) was laid out with an extra 25 mm
routing envelope on each element side, so its surface-to-surface gaps are the
sampled gap plus 50 mm and its bundle widths include the two outer envelopes.
:class:`Revision` carries the difference so that both revisions regenerate
byte-for-byte from the same code; the validator is physical and applies to both.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

MIN_CLEAR_GAP_MM = 25.0
"""Minimum clear gap between insulation surfaces in at least one direction (mm).
Source: published pipe-rack minimum clearance -- VERIFICATION_LOG.md section 6."""
CLEARANCE_MM = MIN_CLEAR_GAP_MM      # name used by earlier releases

KINDS: Tuple[str, ...] = ("pipe", "cable_tray", "duct", "conduit")
SHAPES: Tuple[str, ...] = ("round", "rect")
SURFACE_KINDS: Tuple[str, ...] = ("ceiling", "wall")
TRADES: Tuple[str, ...] = ("domestic", "heating", "chilled", "sprinkler",
                           "electrical", "ventilation")
SERVICES: Tuple[str, ...] = ("domestic_hot", "domestic_cold", "heating", "chilled",
                             "sprinkler", "tray", "duct", "conduit")
WET_TRADES = frozenset({"domestic", "heating", "chilled", "sprinkler"})
ELECTRICAL_KINDS = frozenset({"cable_tray", "conduit"})


@dataclass(frozen=True)
class Revision:
    """What a data revision records.

    ``layout_envelope_mm``: routing envelope added to every element side when
    laying a row out (3.0: 25 mm, so neighbours sit draw + 50 mm apart and the
    recorded bundle width includes 50 mm of empty envelope; 4.0: 0).
    ``element_extra_fields``: per-element fields written beyond the common set.
    """
    version: str
    layout_envelope_mm: float
    element_extra_fields: Tuple[str, ...]


REV_3_0 = Revision("3.0", 25.0, ())
REV_4_0 = Revision("4.0", 0.0, ("span_m", "load_kN_per_m"))
REVISIONS: Dict[str, Revision] = {r.version: r for r in (REV_3_0, REV_4_0)}
CURRENT_REVISION = REV_4_0


def revision_for(version: str) -> Revision:
    """Revision object for a file-level ``version`` string ('3.0', '4.0', '4.1' ...)."""
    major = version.split(".")[0]
    for r in REVISIONS.values():
        if r.version.split(".")[0] == major:
            return r
    raise ValueError(f"unknown data revision {version!r}")


class ContextValidationError(ValueError):
    """Raised by :func:`validate_context` when a context violates an invariant."""


@dataclass(frozen=True)
class Element:
    """One MEP element in the cross-section.  Units: mm, kN, m."""
    kind: str            # pipe | cable_tray | duct | conduit
    service: str         # precise service (domestic_hot, heating, chilled, tray, ...).
                         # With insulation_mm it determines the attachment method a
                         # downstream catalog admits (bare clamp vs rigid insert).
    trade: str           # domestic | heating | chilled | sprinkler | electrical | ventilation
    shape: str           # round | rect
    width_mm: float      # building-horizontal size, bare (no insulation)
    height_mm: float     # building-vertical size, bare
    insulation_mm: float  # per side
    load_kN: float       # per support point = load_kN_per_m x span_m, rounded to 0.01
    label: str
    position_along_mm: float = 0.0
    position_out_mm: float = 0.0
    level: int = 0       # GENERATIVE METADATA: row index of the tiered layout
                         # pattern (0 = nearest the surface).  Not a physical
                         # invariant; consumers must use the continuous
                         # coordinates and pairwise clearance, never rows.
    span_m: Optional[float] = None          # support span the load was derived at
    load_kN_per_m: Optional[float] = None   # operating load per metre of run

    def to_dict(self, revision: Revision = CURRENT_REVISION) -> dict:
        d = {"kind": self.kind, "service": self.service, "trade": self.trade,
             "shape": self.shape, "label": self.label,
             "width_mm": self.width_mm, "height_mm": self.height_mm,
             "insulation_mm": self.insulation_mm, "load_kN": self.load_kN}
        if "span_m" in revision.element_extra_fields:
            d["span_m"] = self.span_m
            d["load_kN_per_m"] = self.load_kN_per_m
        d.update({"level": self.level,
                  "along_mm": round(self.position_along_mm, 1),
                  "out_mm": round(self.position_out_mm, 1)})
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        return cls(kind=d["kind"], service=d["service"], trade=d["trade"],
                   shape=d["shape"], width_mm=float(d["width_mm"]),
                   height_mm=float(d["height_mm"]),
                   insulation_mm=float(d["insulation_mm"]), load_kN=float(d["load_kN"]),
                   label=d["label"], position_along_mm=float(d["along_mm"]),
                   position_out_mm=float(d["out_mm"]), level=int(d["level"]),
                   span_m=None if d.get("span_m") is None else float(d["span_m"]),
                   load_kN_per_m=None if d.get("load_kN_per_m") is None else float(d["load_kN_per_m"]))


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
    """Physical extent ALONG the surface: bare size + insulation on both sides."""
    along = e.width_mm if surface.kind == "ceiling" else e.height_mm
    return along + 2.0 * e.insulation_mm


def depth_out(e: Element, surface: MountingSurface) -> float:
    """Physical extent OUT from the surface: bare size + insulation on both sides."""
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
    revision: Revision = CURRENT_REVISION

    @property
    def total_load_kN(self) -> float:
        # math.fsum is exactly rounded, so the value does not depend on the
        # Python version (3.12 changed sum() to compensated summation, which
        # flips round(x, 2) at .xx5 boundaries for 28 of the 7,000 contexts of
        # revision 3.0 if plain sum() is used on 3.11).
        return math.fsum(e.load_kN for e in self.elements)

    @property
    def n_levels(self) -> int:
        return len({e.level for e in self.elements})

    def _extent(self, envelope_mm: float) -> float:
        lo = min(e.position_along_mm - (span_along(e, self.surface) + 2.0 * envelope_mm) / 2 for e in self.elements)
        hi = max(e.position_along_mm + (span_along(e, self.surface) + 2.0 * envelope_mm) / 2 for e in self.elements)
        return hi - lo

    @property
    def bundle_width_mm(self) -> float:
        """Physical overall extent along the surface (insulation included)."""
        return self._extent(0.0)

    def kind_counts(self) -> Dict[str, int]:
        out = {k: 0 for k in KINDS}
        for e in self.elements:
            out[e.kind] += 1
        return out

    def to_dict(self) -> dict:
        # Key order is part of the release format (files are regenerated
        # byte-for-byte); do not reorder.
        rev = self.revision
        return {
            "context_id": self.context_id, "tier": self.tier,
            "surface": self.surface.to_dict(),
            "n_elements": len(self.elements), "n_levels": self.n_levels,
            "total_load_kN": round(self.total_load_kN, 2),
            "bundle_width_mm": round(self._extent(rev.layout_envelope_mm), 1),
            "elements": [e.to_dict(rev) for e in self.elements],
        }

    @classmethod
    def from_dict(cls, d: dict, revision: Revision = CURRENT_REVISION) -> "MEPContext":
        return cls(elements=tuple(Element.from_dict(e) for e in d["elements"]),
                   surface=MountingSurface.from_dict(d["surface"]),
                   tier=d.get("tier", ""), context_id=d.get("context_id", ""),
                   revision=revision)


# --------------------------------------------------------------------------- #
# Validation                                                                   #
# --------------------------------------------------------------------------- #

POSITION_EPS_MM = 0.5     # positions are stored to 0.1 mm; allow rounding slack
CENTERING_TOL_MM = 1.5    # per-row centring tolerance (two rounded endpoints)


def pair_clearance(a: Element, b: Element, surface: MountingSurface) -> float:
    """Signed physical clear gap between two elements (mm): the larger of the
    along-gap and the out-gap between insulation surfaces.  Negative means the
    elements overlap in both directions.  ``crossmep.tasks.min_clear_gap`` is
    the minimum of this over all pairs."""
    da = abs(a.position_along_mm - b.position_along_mm) - (span_along(a, surface) + span_along(b, surface)) / 2
    do = abs(a.position_out_mm - b.position_out_mm) - (depth_out(a, surface) + depth_out(b, surface)) / 2
    return max(da, do)


def validate_context(ctx: MEPContext) -> None:
    """Raise :class:`ContextValidationError` unless every invariant holds.

    Invariants (every released context of both revisions satisfies them; tests
    enforce them over many unseen seeds):

    1. field domains: kinds, shapes, trades, services, surface kind; positive
       sizes and loads; non-negative insulation; standoff ``out_mm`` > 0;
    2. pairwise clearance: every pair of insulation surfaces is at least
       ``MIN_CLEAR_GAP_MM`` apart ALONG the surface or OUT from it;
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
        if (e.span_m is not None and not e.span_m > 0) or \
                (e.load_kN_per_m is not None and not e.load_kN_per_m > 0):
            raise ContextValidationError(f"{cid}: {e.label}: span and load per metre must be > 0")
    surf = ctx.surface
    els = ctx.elements
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = els[i], els[j]
            if pair_clearance(a, b, surf) < MIN_CLEAR_GAP_MM - POSITION_EPS_MM:
                raise ContextValidationError(
                    f"{cid}: {a.label} and {b.label} are closer than {MIN_CLEAR_GAP_MM:.0f} mm "
                    f"(clear gap {pair_clearance(a, b, surf):.1f} mm)")
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

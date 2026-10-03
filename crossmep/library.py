"""Element library: every physical constant, its source, and its derivation.

Nothing in this module is sampled.  Design parameters that define the benchmark
distribution (trade mix, option weights, surface split) live in
:mod:`crossmep.generate`; the layout constants in :mod:`crossmep.layout`.

Every per-support load is DERIVED here at import time from sourced primitives
(wall thickness, density, span, fill):

    load_kN_per_m = mass_kg_per_m x g / 1000
    load_kN       = round(load_kN_per_m x span_m, 2)

``tests/test_library.py`` pins the derived values to the frozen tables of the
data release, so a change to any primitive is caught by the test suite rather
than silently altering the data.

Status vocabulary (as in VERIFICATION_LOG.md): VERIFIED = primary or
authoritative source; PRACTICE-CITED = practice documents, not a normative
standard; DEFAULT = author choice, disclosed.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

from .model import Element

# --------------------------------------------------------------------------- #
# Physical primitives                                                          #
# --------------------------------------------------------------------------- #

G_M_S2 = 9.81                    # gravitational acceleration (mass -> force)
STEEL_DENSITY_KG_M3 = 7850.0     # carbon steel                                   VERIFIED
WATER_DENSITY_KG_M3 = 1000.0
KNPM_DECIMALS = 4                # precision of the recorded load_kN_per_m

# --------------------------------------------------------------------------- #
# Pipes -- EN 10255:2004 medium series, DN 15-100 (carbon steel)               #
# --------------------------------------------------------------------------- #

DN_SERIES: Tuple[int, ...] = (15, 20, 25, 32, 40, 50, 65, 80, 100)

DN_OD_MM: Dict[int, float] = {15: 21.3, 20: 26.9, 25: 33.7, 32: 42.4, 40: 48.3,
                              50: 60.3, 65: 76.1, 80: 88.9, 100: 114.3}
"""Outside diameters, EN 10220:2002 / EN 10255:2004 (VERIFIED)."""

EN10255_MEDIUM_WALL_MM: Dict[int, float] = {15: 2.6, 20: 2.6, 25: 3.2, 32: 3.2, 40: 3.2,
                                            50: 3.6, 65: 3.6, 80: 4.0, 100: 4.5}
"""Medium-series wall thickness, EN 10255:2004 (VERIFIED)."""

ASME_B311_WATER_SPAN_M: Dict[int, float] = {25: 2.1, 50: 3.0, 80: 3.7, 100: 4.3}
"""ASME B31.1 Table 121.5 suggested support spacing, water service, for NPS 1, 2,
3, 4 (= DN 25, 50, 80, 100), as widely republished (PRACTICE-CITED: the table
itself is paywalled).  Only these published points are used -- see
:func:`support_span_m` -- never interpolated values."""


def support_span_m(dn: int) -> float:
    """Floor rule: each DN takes the span of the largest published size not
    exceeding it; sizes below the smallest published point take that point."""
    below = [k for k in ASME_B311_WATER_SPAN_M if k <= dn]
    key = max(below) if below else min(ASME_B311_WATER_SPAN_M)
    return ASME_B311_WATER_SPAN_M[key]


def pipe_mass_kg_m(dn: int) -> float:
    """Water-filled mass per metre: steel annulus + water at the internal bore."""
    od, t = DN_OD_MM[dn], EN10255_MEDIUM_WALL_MM[dn]
    steel = math.pi * (od - t) * t * 1e-6 * STEEL_DENSITY_KG_M3
    bore = od - 2.0 * t
    water = math.pi / 4.0 * bore ** 2 * 1e-6 * WATER_DENSITY_KG_M3
    return steel + water


def pipe_load_kN_per_m(dn: int) -> float:
    return pipe_mass_kg_m(dn) * G_M_S2 / 1000.0


def pipe_load_kN(dn: int) -> float:
    """Per-support operating load = load per metre x support span, rounded to 0.01 kN."""
    return round(pipe_load_kN_per_m(dn) * support_span_m(dn), 2)


DN_LOAD_KN: Dict[int, float] = {dn: pipe_load_kN(dn) for dn in DN_SERIES}


def insulation_mm(service: str, dn: int) -> float:
    """Code-grounded insulation schedule, per side, by service AND size.

    Heated lines (heating, domestic hot): GEG Anlage 8 '100 %' rule keyed to
    pipe diameter -- 20 mm up to DN20, 30 mm to DN32, then thickness = DN, capped
    at 100 mm (VERIFIED verbatim against the legal text).
    Chilled water (condensation control): 30 mm up to DN40, 50 mm above (UNOG
    2008 employer schedule; VERIFIED as a schedule, not a normative code).
    Domestic cold and sprinkler: bare (thin anti-sweat sleeves excluded;
    DEFAULT, disclosed divergence from GEG 9/19 mm and DIN 1988-200 9 mm).
    """
    if service in ("heating", "domestic_hot"):
        if dn <= 20:
            return 20.0
        if dn <= 32:
            return 30.0
        return float(min(dn, 100))
    if service == "chilled":
        return 30.0 if dn <= 40 else 50.0
    return 0.0


# --------------------------------------------------------------------------- #
# Cable trays -- IEC 61537 systems, manufacturer width series                  #
# --------------------------------------------------------------------------- #

TRAY_WIDTHS_MM: Tuple[int, ...] = (150, 225, 300, 450, 600)   # PRACTICE-CITED series
TRAY_HEIGHT_MM = 60.0            # modelled side height (PRACTICE-CITED common depth)
TRAY_FULL_CABLE_KG_M_AT_300 = 50.0   # 300 mm tray full of power cable, NEC 392 40 %-fill basis (published datum)
TRAY_SELF_KG_M_AT_300 = 5.0          # steel tray self-weight at 300 mm (published weight charts)
TRAY_SPAN_M = 2.0                    # typical tray support spacing (PRACTICE-CITED)


def tray_load_kN_per_m(width_mm: int) -> float:
    """Design-for-full basis: rated fill + self-weight, both scaled linearly with
    width from the 300 mm datum."""
    return (TRAY_FULL_CABLE_KG_M_AT_300 + TRAY_SELF_KG_M_AT_300) * (width_mm / 300.0) * G_M_S2 / 1000.0


def tray_load_kN(width_mm: int) -> float:
    return round(tray_load_kN_per_m(width_mm) * TRAY_SPAN_M, 2)


TRAY_LOAD_KN: Dict[int, float] = {w: tray_load_kN(w) for w in TRAY_WIDTHS_MM}

# --------------------------------------------------------------------------- #
# Ducts -- rectangular (EN 1505 preferred sizes) and round spiral (EN 1506)    #
# --------------------------------------------------------------------------- #

RECT_DUCT_SIZES_MM: Tuple[Tuple[int, int], ...] = ((250, 200), (400, 250), (500, 400),
                                                   (800, 400), (1000, 500))
WALRAVEN_RECT_DUCT_KG_M: Dict[Tuple[int, int], float] = {
    (250, 200): 6.9, (400, 250): 11.7, (500, 400): 16.2, (800, 400): 24.5, (1000, 500): 30.6}
"""Verbatim cells of the Walraven 'Air Duct Dimensions and Weights' table,
non-insulated, including flange/bracing allowance (VERIFIED manufacturer table)."""
DUCT_SPAN_M = 2.4                # 8-ft hanger-spacing practice (PRACTICE-CITED)

ROUND_DUCT_D_MM: Tuple[int, ...] = (160, 200, 250, 315, 400, 500)   # EN 1506:2007 subset (VERIFIED)
SPIRAL_DUCT_SHEET_MM = 0.6       # manufacturer gauge tables for D <= 500 (VERIFIED)


def rect_duct_load_kN_per_m(width_mm: int, height_mm: int) -> float:
    return WALRAVEN_RECT_DUCT_KG_M[(width_mm, height_mm)] * G_M_S2 / 1000.0


def rect_duct_load_kN(width_mm: int, height_mm: int) -> float:
    return round(rect_duct_load_kN_per_m(width_mm, height_mm) * DUCT_SPAN_M, 2)


def round_duct_load_kN_per_m(d_mm: int) -> float:
    """Plain spiral sheet: pi x D x gauge x steel density x g (excl. fittings)."""
    return math.pi * d_mm * 1e-3 * SPIRAL_DUCT_SHEET_MM * 1e-3 * STEEL_DENSITY_KG_M3 * G_M_S2 / 1000.0


def round_duct_load_kN(d_mm: int) -> float:
    return round(round_duct_load_kN_per_m(d_mm) * DUCT_SPAN_M, 3)


RECT_DUCT_LOAD_KN: Dict[Tuple[int, int], float] = {wh: rect_duct_load_kN(*wh) for wh in RECT_DUCT_SIZES_MM}
ROUND_DUCT_LOAD_KN: Dict[int, float] = {d: round_duct_load_kN(d) for d in ROUND_DUCT_D_MM}

# --------------------------------------------------------------------------- #
# Electrical conduits -- IEC 61386-1 metric sizes (specified by outer diameter) #
# --------------------------------------------------------------------------- #

CONDUIT_OD_MM: Tuple[int, ...] = (20, 25, 32, 40, 50)   # strict subset of IEC 61386-1 (VERIFIED)
CONDUIT_WALL_MM = 1.5            # BS 4568 / IEC 61386-21 class range 1.2-1.6 mm (VERIFIED)
CABLE_FILL_FRACTION = 0.40       # IEC/NEC 40 %-of-bore fill
CABLE_BULK_DENSITY_KG_M3 = 4167.0
"""Effective bulk density of installed cable, back-derived from the published
tray datum: 50 kg/m / (0.40 fill x 0.300 m x 0.100 m) = 4,167 kg/m3."""
CONDUIT_SPAN_M = 2.0             # conduit support spacing (PRACTICE-CITED)


def conduit_load_kN_per_m(od_mm: int) -> float:
    steel = math.pi * (od_mm - CONDUIT_WALL_MM) * CONDUIT_WALL_MM * 1e-6 * STEEL_DENSITY_KG_M3
    bore = od_mm - 2.0 * CONDUIT_WALL_MM
    cable = math.pi / 4.0 * bore ** 2 * 1e-6 * CABLE_FILL_FRACTION * CABLE_BULK_DENSITY_KG_M3
    return (steel + cable) * G_M_S2 / 1000.0


def conduit_load_kN(od_mm: int) -> float:
    return round(conduit_load_kN_per_m(od_mm) * CONDUIT_SPAN_M, 3)


CONDUIT_LOAD_KN: Dict[int, float] = {od: conduit_load_kN(od) for od in CONDUIT_OD_MM}

# --------------------------------------------------------------------------- #
# Element constructors (pure; no sampling)                                     #
# --------------------------------------------------------------------------- #

PIPE_TRADES: Tuple[str, ...] = ("domestic", "heating", "chilled", "sprinkler")

TRADE_DN_BAND: Dict[str, Tuple[int, int]] = {
    "domestic": (15, 32), "heating": (20, 65), "chilled": (25, 100), "sprinkler": (25, 100)}
"""Inclusive DN band each pipe trade is drawn from (DEFAULT, disclosed)."""


def dn_band(trade: str) -> list:
    lo, hi = TRADE_DN_BAND[trade]
    return [dn for dn in DN_SERIES if lo <= dn <= hi]


def _knpm(x: float) -> float:
    return round(x, KNPM_DECIMALS)


def make_pipe(dn: int, service: str, trade: str) -> Element:
    od = DN_OD_MM[dn]
    return Element("pipe", service, trade, "round", od, od,
                   insulation_mm(service, dn), DN_LOAD_KN[dn], f"DN{dn}",
                   span_m=support_span_m(dn), load_kN_per_m=_knpm(pipe_load_kN_per_m(dn)))


def make_tray(width_mm: int) -> Element:
    return Element("cable_tray", "tray", "electrical", "rect", float(width_mm),
                   TRAY_HEIGHT_MM, 0.0, TRAY_LOAD_KN[width_mm], f"{width_mm} tray",
                   span_m=TRAY_SPAN_M, load_kN_per_m=_knpm(tray_load_kN_per_m(width_mm)))


def make_rect_duct(width_mm: int, height_mm: int) -> Element:
    # Duct thermal insulation is excluded: no verified thickness source (DATASHEET).
    return Element("duct", "duct", "ventilation", "rect", float(width_mm), float(height_mm),
                   0.0, RECT_DUCT_LOAD_KN[(width_mm, height_mm)], f"{width_mm}x{height_mm} duct",
                   span_m=DUCT_SPAN_M, load_kN_per_m=_knpm(rect_duct_load_kN_per_m(width_mm, height_mm)))


def make_round_duct(d_mm: int) -> Element:
    return Element("duct", "duct", "ventilation", "round", float(d_mm), float(d_mm),
                   0.0, ROUND_DUCT_LOAD_KN[d_mm], f"Ø{d_mm} duct",
                   span_m=DUCT_SPAN_M, load_kN_per_m=_knpm(round_duct_load_kN_per_m(d_mm)))


def make_conduit(od_mm: int) -> Element:
    return Element("conduit", "conduit", "electrical", "round", float(od_mm), float(od_mm),
                   0.0, CONDUIT_LOAD_KN[od_mm], f"Ø{od_mm} conduit",
                   span_m=CONDUIT_SPAN_M, load_kN_per_m=_knpm(conduit_load_kN_per_m(od_mm)))

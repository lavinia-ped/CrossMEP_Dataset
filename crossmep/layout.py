"""Layout engine: stack element groups into rows, lay each row out ALONG the
surface with measurement-fitted clear gaps, stagger OUT within the row.

Rows (generative metadata)
--------------------------
Groups are sorted by vertical priority (bulky services nearest the surface:
ducts, then trays/conduits, then pipes).  With ``n_rows`` rows, the first
``n_rows - 1`` groups each take their own row and every remaining group shares
the last row.  ``level`` records the row index; it is metadata, not a physical
invariant.

Clear gaps
----------
The clear gap between the insulation surfaces of along-adjacent elements is
drawn from a lognormal fitted to clear gaps measured on the open Duplex
Apartment MEP model above the published 25 mm minimum (n = 73, < 600 mm; see
``verify/compare_gaps.py``), floored at ``GAP_FLOOR_MM`` and capped at
``GAP_CAP_MM``.  In data revision 4.0 the draw IS the physical gap.  Revision
3.0 additionally padded every element with a 25 mm routing envelope on each
side (``envelope_mm`` below), which placed neighbours draw + 50 mm apart; the
parameter exists only to regenerate those files.

Stagger
-------
Within a row, each element's standoff is offset by a half-normal draw with
scale ``stagger`` (0 for single elements, 75 mm up to five elements, 120 mm
above), capped at ``STAGGER_CAP_SIGMAS`` scales, calibrated to the measured
in-bundle elevation spread.  Stagger is safe because elements in a row are
already cleared ALONG the surface.

Wall rule
---------
On walls, electrical containment is sorted ABOVE wet services within a row
(smaller ``along`` = higher elevation): BS 7671 Reg. 528.3.2 requires a wiring
system routed below condensation-prone services to be protected; keeping the
containment above the wet services satisfies it without added protection.
"""
from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Tuple

import numpy as np

from .model import Element, MountingSurface, span_along, depth_out, ELECTRICAL_KINDS

GAP_FLOOR_MM = 25.0
"""Hard floor on the sampled clear gap: the published pipe-rack minimum
(VERIFICATION_LOG.md section 6).  The same floor applies inside and between
trades; larger separations arise from the fitted distribution."""
GAP_CAP_MM = 500.0               # design parameter (DEFAULT)
GAP_LOGNORMAL_MU = 5.018         # fitted to Duplex MEP clear gaps > 25 mm, < 600 mm
GAP_LOGNORMAL_SIGMA = 0.848      # (n = 73, KS p = 0.53); see verify/compare_gaps.py
ROW_VGAP_MM = 120.0              # clear gap between stacked rows, OUT direction (DEFAULT)
TOP_OFFSET_MM = 90.0             # standoff of the first row from the surface (DEFAULT)
STAGGER_CAP_SIGMAS = 2.5

VPRIORITY = {"duct": 0, "cable_tray": 1, "conduit": 1, "pipe": 2}
"""Lower value sits nearer the surface (PRACTICE-CITED tiering order; the
coordination criteria behind it follow Korman, Fischer & Tatum 2003)."""


def sample_gap(rng: Optional[np.random.Generator], floor: float = GAP_FLOOR_MM) -> float:
    """One clear-gap draw: lognormal, floored, capped.  ``rng=None`` returns the floor."""
    if rng is None:
        return floor
    draw = float(np.exp(rng.normal(GAP_LOGNORMAL_MU, GAP_LOGNORMAL_SIGMA)))
    return float(min(max(floor, draw), GAP_CAP_MM))


def arrange(groups: List[Tuple[int, List[Element]]], n_rows: int,
            surface: MountingSurface, stagger: float,
            rng: Optional[np.random.Generator] = None,
            envelope_mm: float = 0.0) -> List[Element]:
    """Place grouped elements; returns elements with positions and ``level`` set.

    The order of random draws (one gap per adjacent pair while laying the row
    out, then one stagger draw per element) is part of the frozen stream and is
    identical for both data revisions; ``envelope_mm`` only changes arithmetic.
    """
    groups = sorted(groups, key=lambda g: g[0])          # stable: ties keep insertion order
    n_rows = max(1, min(n_rows, len(groups)))
    rows: List[List[Element]] = [[] for _ in range(n_rows)]
    for i, (_prio, els) in enumerate(groups):
        rows[min(i, n_rows - 1)].extend(els)

    def extent(e: Element) -> float:
        return span_along(e, surface) + 2.0 * envelope_mm

    out: List[Element] = []
    cursor = TOP_OFFSET_MM
    for ri, row in enumerate(rows):
        if surface.kind == "wall":
            row = sorted(row, key=lambda e: 0 if e.kind in ELECTRICAL_KINDS else 1)
        # lay out ALONG the surface
        centres: List[float] = []
        x = 0.0
        for j, e in enumerate(row):
            sp = extent(e)
            if j == 0:
                x = sp / 2.0
            else:
                gap = sample_gap(rng)                      # same floor within and between trades
                x = centres[-1] + extent(row[j - 1]) / 2.0 + gap + sp / 2.0
            centres.append(x)
        mid = (centres[0] - extent(row[0]) / 2.0 + centres[-1] + extent(row[-1]) / 2.0) / 2.0
        # stagger OUT within the row
        if rng is None or stagger <= 0:
            douts = [stagger * (j % 2) for j in range(len(row))]
        else:
            douts = [float(min(abs(rng.normal(0.0, stagger)), STAGGER_CAP_SIGMAS * stagger))
                     for _ in range(len(row))]
        near = [douts[j] - depth_out(row[j], surface) / 2.0 for j in range(len(row))]
        far = [douts[j] + depth_out(row[j], surface) / 2.0 for j in range(len(row))]
        shift = cursor - min(near)
        for j, e in enumerate(row):
            out.append(replace(e, position_along_mm=round(centres[j] - mid, 1),
                               position_out_mm=round(douts[j] + shift, 1), level=ri))
        cursor = max(far) + shift + ROW_VGAP_MM
    return out

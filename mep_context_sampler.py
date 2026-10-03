"""Backward-compatible entry point for the v3.x single-file API.

The generator now lives in the ``crossmep`` package (see README.md).  This
module re-exports the names earlier releases documented so that

    from mep_context_sampler import generate_custom, generate_dataset, validate_context
    python mep_context_sampler.py --n 1000 --seed 42 --json out.json

keep working.  Output is the CURRENT data revision (4.0); pass
``revision="3.0"`` to ``generate_dataset`` for the paper-release geometry.
New code should use ``crossmep`` / ``python -m crossmep``.
"""
from __future__ import annotations

import sys

from crossmep.generate import (CANONICAL_SPLITS, TIERS, generate_context, generate_custom,  # noqa: F401
                               generate_dataset, generate_split)
from crossmep.layout import (GAP_CAP_MM, GAP_FLOOR_MM, GAP_LOGNORMAL_MU, GAP_LOGNORMAL_SIGMA,  # noqa: F401
                             ROW_VGAP_MM, TOP_OFFSET_MM, VPRIORITY, arrange)
from crossmep.library import (CONDUIT_LOAD_KN, CONDUIT_OD_MM, DN_LOAD_KN, DN_OD_MM,  # noqa: F401
                              RECT_DUCT_LOAD_KN, RECT_DUCT_SIZES_MM, ROUND_DUCT_D_MM,
                              ROUND_DUCT_LOAD_KN, TRAY_HEIGHT_MM, TRAY_LOAD_KN, TRAY_WIDTHS_MM,
                              insulation_mm)
from crossmep.model import (CLEARANCE_MM, MIN_CLEAR_GAP_MM, REV_3_0, REV_4_0,  # noqa: F401
                            ContextValidationError, Element, MEPContext, MountingSurface,
                            depth_out, span_along, validate_context)
from crossmep.render import context_svg, render_gallery_html  # noqa: F401

# v3.x names.  NOTE: span_along is now physical (bare + insulation); the v3.0
# routing envelope is applied only when regenerating revision 3.0 files.
_span = span_along
_depth = depth_out
_arrange = arrange
TRAY_WIDTHS = list(TRAY_WIDTHS_MM)
DUCT_SIZES = list(RECT_DUCT_SIZES_MM)
DUCT_LOAD_KN = {w: v for (w, _h), v in RECT_DUCT_LOAD_KN.items()}
ROUND_DUCT_D = list(ROUND_DUCT_D_MM)
CONDUIT_OD = list(CONDUIT_OD_MM)
GAP_INTRA_MM = GAP_INTER_MM = GAP_FLOOR_MM


def render_preview_html(contexts, path: str) -> str:
    """Kept for compatibility: a plain (non-interactive) card page."""
    cards = "".join(f'<div class="card"><div class="hd"><span class="id">{c.context_id} · {c.tier}</span>'
                    f'<span class="tr">{", ".join(sorted({e.trade for e in c.elements}))}</span></div>'
                    f'{context_svg(c)}</div>' for c in contexts)
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
            "*{box-sizing:border-box}body{margin:0;padding:20px;background:#f7f9fb;"
            "font-family:ui-sans-serif,system-ui,sans-serif;color:#1f2933}"
            ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;align-items:start}"
            ".card{background:#fff;border:1px solid #d4dce2;border-radius:12px;padding:10px}"
            ".hd{display:flex;justify-content:space-between;margin-bottom:4px}"
            ".id{font-family:ui-monospace,monospace;font-size:12px;color:#5a6b78}"
            ".tr{font-size:11px;color:#3e4c59}</style></head><body>"
            f"<div class='grid'>{cards}</div></body></html>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


if __name__ == "__main__":
    # Translate the v3.x flags onto `python -m crossmep generate`.
    import argparse

    from crossmep.cli import main

    ap = argparse.ArgumentParser(description="Deprecated entry point; use `python -m crossmep generate`.")
    ap.add_argument("--n", type=int, default=320)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tier", default=None, choices=list(TIERS))
    for k in ("pipes", "trays", "ducts", "conduits"):
        ap.add_argument(f"--{k}", type=int, default=None)
    ap.add_argument("--surface", default=None, choices=["ceiling", "wall"])
    ap.add_argument("--json", default="mep_contexts.json")
    ap.add_argument("--gallery", default="mep_contexts_gallery.html")
    a = ap.parse_args()
    argv = ["generate", "--n", str(a.n), "--seed", str(a.seed), "--out", a.json, "--gallery", a.gallery]
    if a.tier:
        argv += ["--tier", a.tier]
    for k in ("pipes", "trays", "ducts", "conduits"):
        if getattr(a, k) is not None:
            argv += [f"--{k}", str(getattr(a, k))]
    if a.surface:
        argv += ["--surface", a.surface]
    sys.exit(main(argv))

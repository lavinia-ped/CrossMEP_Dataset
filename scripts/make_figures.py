#!/usr/bin/env python3
"""Regenerate the presentation figures in docs/figures/ from the released data.

    pip install matplotlib "qrcode[pil]"
    python scripts/make_figures.py            # writes docs/figures/* and prints the context ids used

Figures (benchmark split of the current data revision; 200 dpi):

    01_what_a_context_is.png    one C5 ceiling section with its fields called out
    02_tier_gallery.png         one context per tier, C1 to C8, ceilings and walls
    03_tiers_stats.png          per-tier minimum clear gap and total load, benchmark boxes and the
                                population median of 2,000 generated contexts per tier (verify/tier_trends.py)
    04_gaps_vs_buildings.png    generated pipe gaps vs pipe gaps measured on sections of two open
                                buildings, with Wasserstein-1 distances and intervals (verify/compare_sections.py)
    05_generation_example.png   one generated context with its rows and a sampled gap annotated
    06_catalog_coverage.png     which pipe sizes the paper's two-size clamp catalog attaches, and the best
                                share any k sizes could (verify/catalog_stress.py)
    title_art.png               a congested section in light ink for the dark title slide
    deck_data.json              every number the slide deck prints (docs/deck/build_deck.js)
    qr_repo.png                 QR code of the repository URL

Style: light chart surface, thin marks, hairline solid gridlines, text in ink
tokens; trade identity by colour PLUS a text label on every element, so nothing
depends on colour alone.  Palette: the reference categorical slots of the
data-visualisation guideline (blue, orange, aqua, red, violet, green); the six
trade colours were run through its validator (light surface): all hard gates
pass; the red/aqua pair sits in the 6-8 CVD band and aqua is below 3:1
contrast, both of which the guideline allows only with secondary encoding --
here the per-element text labels and the legend.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import crossmep.catalog as catalog  # noqa: E402
import crossmep.tasks as cm  # noqa: E402
from crossmep.generate import CANONICAL_SPLITS  # noqa: E402
from crossmep.layout import GAP_CAP_MM, GAP_LOGNORMAL_MU, GAP_LOGNORMAL_SIGMA  # noqa: E402

OUT = os.path.join(ROOT, "docs", "figures")
SPLITS = ("train", "val", "test", "benchmark")

# --- style tokens -------------------------------------------------------------
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA, RED, VIOLET, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#4a3aa7", "#008300"
TRADE_COLOR = {"domestic": BLUE, "heating": ORANGE, "chilled": AQUA, "sprinkler": RED,
               "electrical": VIOLET, "ventilation": GREEN}
TRADE_NAME = {"domestic": "domestic water", "heating": "heating", "chilled": "chilled water",
              "sprinkler": "sprinkler", "electrical": "electrical", "ventilation": "ventilation"}
SLAB_MM = 60.0                                  # drawn thickness of the surface band

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 8,
    "ytick.labelsize": 8, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "axes.spines.top": False, "axes.spines.right": False, "grid.color": GRID, "grid.linewidth": 0.8,
    "grid.linestyle": "-", "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "legend.frameon": False, "legend.fontsize": 8,
})


def _verify_module(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "verify", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _compare_gaps_module():
    return _verify_module("compare_gaps")


# --- drawing a context ----------------------------------------------------------
# Screen frame: ceiling -> x = along, y = -out (slab on top);
#               wall    -> x = out,   y = -along (wall on the left; smaller along = higher).
# Element width/height are screen-horizontal/vertical in both frames.

def _centre(e, sk):
    return (e["along_mm"], -e["out_mm"]) if sk == "ceiling" else (e["out_mm"], -e["along_mm"])


def content_bbox(ctx):
    sk = ctx["surface"]["kind"]
    xs, ys = [], []
    for e in ctx["elements"]:
        cx, cy = _centre(e, sk)
        w, h, ins = e["width_mm"], e["height_mm"], e["insulation_mm"]
        xs += [cx - w / 2 - ins, cx + w / 2 + ins]
        ys += [cy - h / 2 - ins, cy + h / 2 + ins]
    return min(xs), max(xs), min(ys), max(ys)


def draw_elements(ax, ctx, label_elements=True, label_size=6.5, dedup_mm=320.0):
    """Draw every element; a conduit group within ``dedup_mm`` carries one label."""
    sk = ctx["surface"]["kind"]
    placed = []
    def _label_ok(text, x, y):
        if "conduit" in text and any(t == text and abs(x - px) < dedup_mm and abs(y - py) < dedup_mm for t, px, py in placed):
            return False
        placed.append((text, x, y))
        return True
    for e in ctx["elements"]:
        cx, cy = _centre(e, sk)
        w, h, ins = e["width_mm"], e["height_mm"], e["insulation_mm"]
        col = TRADE_COLOR[e["trade"]]
        if e["shape"] == "round":
            if ins > 0:
                ax.add_patch(Circle((cx, cy), w / 2 + ins, fill=False, ec=col, lw=0.8, ls=(0, (2, 2)), alpha=0.7))
            ax.add_patch(Circle((cx, cy), w / 2, fill=False, ec=col, lw=1.6))
            if label_elements and _label_ok(e["label"], cx, cy):
                ax.text(cx, cy - w / 2 - ins - 12, e["label"], ha="center", va="top", fontsize=label_size, color=INK2)
        else:
            ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fill=True, fc=col, alpha=0.08, ec=col, lw=1.6))
            if label_elements and _label_ok(e["label"], cx, cy):
                ax.text(cx, cy, e["label"], ha="center", va="center", fontsize=label_size, color=INK2)


def draw_surface(ax, ctx, lo, hi, label=True):
    """Hatched slab along the top (ceiling) or wall along the left, spanning lo..hi."""
    s = ctx["surface"]
    if s["kind"] == "ceiling":
        ax.add_patch(Rectangle((lo, 0), hi - lo, SLAB_MM, fc="#efeeea", ec=AXIS, lw=0.8, hatch="////", zorder=0))
        if label:
            ax.text(lo + 10, SLAB_MM / 2, f"slab · {s['substrate']} · {s['thickness_mm']:.0f} mm",
                    va="center", fontsize=6.5, color=INK2, bbox=dict(fc=SURFACE, ec="none", pad=1.2))
    else:
        ax.add_patch(Rectangle((-SLAB_MM, lo), SLAB_MM, hi - lo, fc="#efeeea", ec=AXIS, lw=0.8, hatch="////", zorder=0))


def fit_limits(fig, ax, x0, x1, y0, y1, scale=None, anchor="top"):
    """Set limits so the content fits the axes box at an explicit mm-per-inch
    scale (the max needed, unless given), keeping aspect equal without letting
    matplotlib resize the box.  anchor: 'top' (ceiling), 'left' (wall) or 'centre'."""
    pos = ax.get_position()
    fw, fh = fig.get_size_inches()
    bw, bh = pos.width * fw, pos.height * fh
    need = max((x1 - x0) / bw, (y1 - y0) / bh)
    s = need if scale is None else max(scale, need)
    if anchor == "left":
        ax.set_xlim(x0, x0 + s * bw)
    else:
        cx = (x0 + x1) / 2
        ax.set_xlim(cx - s * bw / 2, cx + s * bw / 2)
    if anchor == "top":
        ax.set_ylim(y1 - s * bh, y1)
    else:
        cy = (y0 + y1) / 2
        ax.set_ylim(cy - s * bh / 2, cy + s * bh / 2)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return s


def draw_context(fig, ax, ctx, title=None, scale=None, min_extent=600.0, label_elements=True,
                 surface_label=True, label_size=6.5, title_size=9):
    x0, x1, y0, y1 = content_bbox(ctx)
    if ctx["surface"]["kind"] == "ceiling":
        width = max(x1 - x0, min_extent)
        cx = (x0 + x1) / 2
        fit_limits(fig, ax, cx - width / 2 - 30, cx + width / 2 + 30, y0 - 45, SLAB_MM + 2, scale, "top")
        xl = ax.get_xlim()
        draw_surface(ax, ctx, xl[0] + 0.01 * (xl[1] - xl[0]), xl[1] - 0.01 * (xl[1] - xl[0]), surface_label)
    else:
        height = max(y1 - y0, min_extent)
        cy = (y0 + y1) / 2
        fit_limits(fig, ax, -SLAB_MM - 2, x1 + 40, cy - height / 2 - 45, cy + height / 2 + 20, scale, "left")
        yl = ax.get_ylim()
        draw_surface(ax, ctx, yl[0] + 0.01 * (yl[1] - yl[0]), yl[1] - 0.01 * (yl[1] - yl[0]), False)
    draw_elements(ax, ctx, label_elements, label_size)
    if title:
        ax.set_title(title, loc="left", fontsize=title_size)


def dimension(ax, ctx, a, b, label, below=30, fontsize=7.5, label_align="center", row_bottom=None):
    """Dimension line between the insulation surfaces of elements a and b (ceiling frame)."""
    ea, eb = ctx["elements"][a], ctx["elements"][b]
    xa = ea["along_mm"] + ea["width_mm"] / 2 + ea["insulation_mm"]
    xb = eb["along_mm"] - eb["width_mm"] / 2 - eb["insulation_mm"]
    bottom = min(-e["out_mm"] - e["height_mm"] / 2 - e["insulation_mm"] for e in (ea, eb))
    if row_bottom is not None:                 # clear every label in the row
        y = min(bottom, row_bottom) - below
    else:
        y = bottom - below
    ax.annotate("", xy=(xa, y), xytext=(xb, y), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
    for x in (xa, xb):
        ax.plot([x, x], [y - 6, bottom], color=INK, lw=0.5, alpha=0.6)
    lx = {"center": (xa + xb) / 2, "left": xa, "right": xb}[label_align]
    ax.text(lx, y - 10, label, ha=label_align, va="top", fontsize=fontsize, color=INK, fontweight="bold")


def trade_legend(fig, trades, y=0.03):
    order = [t for t in TRADE_COLOR if t in set(trades)]
    handles = [plt.Line2D([], [], color=TRADE_COLOR[t], lw=1.8, label=TRADE_NAME[t]) for t in order]
    fig.legend(handles=handles, loc="lower center", ncol=len(order), bbox_to_anchor=(0.5, y), handlelength=1.6)


# --- figure 1: what a context is ----------------------------------------------

def fig_what_a_context_is(bench):
    ctx = next(c for c in bench if c["tier"] == "C5" and c["surface"]["kind"] == "ceiling"
               and len({e["trade"] for e in c["elements"]}) >= 3 and c["n_levels"] == 2)
    fig = plt.figure(figsize=(10, 4.6))
    ax = fig.add_axes([0.02, 0.12, 0.52, 0.80])
    draw_context(fig, ax, ctx, title=f"One context ({ctx['context_id']}, tier {ctx['tier']}): the section at a support location")
    txt = fig.add_axes([0.57, 0.08, 0.42, 0.84])
    txt.axis("off")
    rows = [("element", "trade", "ins", "kN/m", "span", "kN")]
    for e in ctx["elements"]:
        rows.append((e["label"], TRADE_NAME[e["trade"]], f"{e['insulation_mm']:.0f}", f"{e['load_kN_per_m']:.3f}",
                     f"{e['span_m']:.1f} m", f"{e['load_kN']:.2f}"))
    txt.text(0, 0.98, "What the support designer is given", fontsize=9, fontweight="bold", color=INK, va="top")
    y = 0.90
    for i, r in enumerate(rows):
        line = f"{r[0]:<14}{r[1]:<16}{r[2]:>4}{r[3]:>8}{r[4]:>7}{r[5]:>7}"
        txt.text(0, y, line, fontsize=7.4, family="monospace", color=MUTED if i == 0 else INK2, va="top")
        y -= 0.062
    y -= 0.03
    for s in (f"surface: {ctx['surface']['kind']}, {ctx['surface']['substrate']}, {ctx['surface']['thickness_mm']:.0f} mm",
              f"total load at this support: {ctx['total_load_kN']:.2f} kN  (ins = insulation per side, mm)",
              f"bundle width {ctx['bundle_width_mm']:.0f} mm, {ctx['n_levels']} rows, closest pair {cm.min_clear_gap(ctx):.0f} mm clear"):
        txt.text(0, y, s, fontsize=7.8, color=INK2, va="top")
        y -= 0.065
    txt.text(0, y - 0.04, "Not given - that is the answer: channel, rods, clamps, anchors.",
             fontsize=8.2, fontweight="bold", color=INK, va="top")
    trade_legend(fig, {e["trade"] for e in ctx["elements"]}, y=0.02)
    fig.savefig(os.path.join(OUT, "01_what_a_context_is.png"), dpi=200)
    plt.close(fig)
    return ctx["context_id"]


# --- figure 2: one context per tier -------------------------------------------

GALLERY_PICKS = {
    "C1": ("ceiling", lambda c: c["elements"][0]["kind"] == "pipe" and c["elements"][0]["insulation_mm"] > 0),
    "C2": ("wall", lambda c: len({e["kind"] for e in c["elements"]}) == 2),
    "C3": ("ceiling", lambda c: len({e["kind"] for e in c["elements"]}) >= 2),
    "C4": ("ceiling", lambda c: any(e["kind"] == "duct" for e in c["elements"]) and c["n_levels"] == 2),
    "C5": ("wall", lambda c: c["n_levels"] == 2 and len({e["kind"] for e in c["elements"]}) >= 2),
    "C6": ("ceiling", lambda c: any(e["kind"] == "conduit" for e in c["elements"])
           and any(e["kind"] == "pipe" for e in c["elements"]) and c["n_levels"] >= 2),
    "C7": ("ceiling", lambda c: c["n_levels"] == 3 and len({e["trade"] for e in c["elements"]}) >= 3),
    "C8": ("ceiling", lambda c: c["n_levels"] == 3 and len({e["trade"] for e in c["elements"]}) >= 3),
}


def pick_gallery(bench):
    picks = {}
    for tier, (surface, want) in GALLERY_PICKS.items():
        pool = [c for c in bench if c["tier"] == tier]
        picks[tier] = next((c for c in pool if c["surface"]["kind"] == surface and want(c)),
                           next(c for c in pool if c["surface"]["kind"] == surface))
    return picks


def fig_tier_gallery(bench):
    picks = pick_gallery(bench)
    fig = plt.figure(figsize=(12, 5.6))
    cols, rows = 4, 2
    left, right, top, bottom, hgap, vgap = 0.01, 0.99, 0.93, 0.09, 0.02, 0.09
    pw = (right - left - hgap * (cols - 1)) / cols
    ph = (top - bottom - vgap * (rows - 1)) / rows
    for i, (tier, ctx) in enumerate(picks.items()):
        r, c = divmod(i, cols)
        ax = fig.add_axes([left + c * (pw + hgap), top - (r + 1) * ph - r * vgap, pw, ph])
        n = ctx["n_elements"]
        title = (f"{tier}  ·  {ctx['surface']['kind']}  ·  {n} element{'s' if n > 1 else ''}  ·  "
                 f"{ctx['total_load_kN']:.2f} kN")
        draw_context(fig, ax, ctx, title=title, min_extent=500.0, surface_label=False, label_size=6, title_size=8.5)
    trade_legend(fig, {e["trade"] for c in picks.values() for e in c["elements"]}, y=0.005)
    fig.savefig(os.path.join(OUT, "02_tier_gallery.png"), dpi=200)
    plt.close(fig)
    return {t: c["context_id"] for t, c in picks.items()}


# --- figure 3: tier statistics --------------------------------------------------

def _box(ax, data, labels, color, ylabel, title, fmt):
    ax.boxplot(data, widths=0.42, patch_artist=True, showfliers=False, medianprops=dict(color=INK, lw=1.4),
               boxprops=dict(facecolor=color, alpha=0.18, edgecolor=color, lw=1.2),
               whiskerprops=dict(color=color, lw=1.0), capprops=dict(color=color, lw=1.0))
    ax.set_xticks(range(1, len(labels) + 1), labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    for i, d in enumerate(data, start=1):
        if i in (1, len(data)):
            ax.text(i + 0.26, np.median(d), fmt.format(np.median(d)), va="center", ha="left", fontsize=7.5, color=INK)


def fig_tier_stats(bench, trends):
    tiers = [f"C{n}" for n in range(1, 9)]
    gaps = [[cm.min_clear_gap(c) for c in bench if c["tier"] == t and c["n_elements"] > 1] for t in tiers[1:]]
    loads = [[c["total_load_kN"] for c in bench if c["tier"] == t] for t in tiers]
    pop = trends["population"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.9))
    g2, g8 = np.median(gaps[0]), np.median(gaps[-1])
    l1, l8 = np.median(loads[0]), np.median(loads[-1])
    _box(a, gaps, tiers[1:], BLUE, "minimum clear gap between elements (mm)",
         f"Tighter overall: median gap {g2:.0f} mm (C2) to {g8:.0f} mm (C8)", "{:.0f}")
    _box(b, loads, tiers, BLUE, "total load at the support (kN)",
         f"Heavier at every step: {l1:.2f} kN (C1) to {l8:.2f} kN (C8)", "{:.2f}")
    a.plot(range(1, 8), [pop["clear_gap_mm"]["per_tier"][t]["median"] for t in tiers[1:]], ls="none", marker="D",
           ms=4.5, color=ORANGE, zorder=5, label="median of 2,000 generated contexts per tier")
    b.plot(range(1, 9), [pop["load_kN"]["per_tier"][t]["median"] for t in tiers], ls="none", marker="D",
           ms=4.5, color=ORANGE, zorder=5, label="median of 2,000 generated contexts per tier")
    a.axvspan(4.5, 7.5, color=GRID, alpha=0.45, zorder=0, lw=0)
    a.text(6.0, 432, "from C6: two or three rows", ha="center", va="top", fontsize=7.5, color=INK2)
    a.set_ylim(0, 450)
    b.set_ylim(0, 6.5)
    a.legend(loc="upper right", bbox_to_anchor=(1.0, 0.91), fontsize=7.5)
    fig.text(0.01, 0.045, "Boxes: benchmark split, 125 contexts per tier (interquartile range, median line, whiskers 1.5 IQR).",
             fontsize=7, color=MUTED)
    fig.text(0.01, 0.012, "From C6 the generator stacks elements in two or three rows, so the elements per row drop and the closest gap widens again.",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.075, 1, 1))
    fig.savefig(os.path.join(OUT, "03_tiers_stats.png"), dpi=200)
    plt.close(fig)


# --- figure 4: generated vs measured pipe gaps on sections of two buildings -----

def fig_gaps_vs_buildings(bench, sec):
    cs = _verify_module("compare_sections")
    gen = np.concatenate(cs.generated_samples(bench))
    gc, wc = cs.measured_sample(cs.load_measured("clinic_plumbing"))
    fig, (ax, fx) = plt.subplots(1, 2, figsize=(10.6, 4.3), gridspec_kw={"width_ratios": [1.0, 1.15]})
    bins = np.arange(0, 601, 25)
    ax.hist(gc, bins=bins, weights=wc, density=True, color=BLUE, alpha=0.5,
            label=f"measured: Medical-Dental Clinic, {len(gc)} pipe pairs")
    ax.hist(gen, bins=bins, density=True, histtype="step", color=ORANGE, lw=2.0,
            label=f"generated: CrossMEP benchmark, {len(gen):,} pipe pairs")
    ax.set_xlim(0, 600)
    ax.set_ylim(0, 0.0062)
    ax.set_yticks([])
    ax.set_ylabel("share of pipe pairs")
    ax.set_xlabel("clear gap between neighbouring pipes, bare surfaces (mm)")
    ax.legend(loc="upper right", fontsize=7.5)
    ax.set_title("A building the generator never saw", loc="left")

    g, r = sec["gen_to_real"], sec["real_to_real"]
    L = "length_weighted"
    rows = [("generated  \u2194  Clinic", g["clinic_plumbing"][L], ORANGE),
            ("Duplex MEP  \u2194  Duplex Plumbing", r["duplex_mep|duplex_plumbing"][L], BLUE),
            ("generated  \u2194  Duplex MEP", g["duplex_mep"][L], ORANGE),
            ("Clinic  \u2194  Duplex MEP", r["clinic_plumbing|duplex_mep"][L], BLUE),
            ("generated  \u2194  Duplex Plumbing", g["duplex_plumbing"][L], ORANGE),
            ("Clinic  \u2194  Duplex Plumbing", r["clinic_plumbing|duplex_plumbing"][L], BLUE)]
    y = np.arange(len(rows))[::-1]
    for yi, (label, v, col) in zip(y, rows):
        fx.plot([v["lo"], v["hi"]], [yi, yi], color=col, lw=2.2, solid_capstyle="butt")
        fx.plot([v["w1"]], [yi], marker="o", ms=6, color=col)
        fx.text(v["hi"] + 4, yi, f"{v['w1']:.0f}", va="center", fontsize=8, color=INK)
        if "noise_floor" in v:
            fx.plot([v["noise_floor"]["median"]], [yi], marker="|", ms=11, mew=1.6, color=MUTED)
    fixed = g["clinic_plumbing"][L]["fixed_25mm"]
    fx.set_yticks(y, [x[0] for x in rows], fontsize=8)
    fx.set_xlim(0, 160)
    fx.set_ylim(-0.7, len(rows) - 0.3)
    fx.xaxis.grid(True)
    fx.set_axisbelow(True)
    fx.set_xlabel("Wasserstein-1 distance (mm) with 95 % interval;  | = noise floor")
    fx.set_title("Distances: generated (orange) and real (blue) models", loc="left")
    fx.text(158, -0.55, f"a fixed 25 mm gap would be {fixed:.0f} mm from the clinic", ha="right", va="bottom",
            fontsize=7.5, color=INK2)
    fig.text(0.01, 0.045, "Sections every 250 mm through the buildingSMART Duplex Apartment (MEP and Plumbing models) and "
             "Medical-Dental Clinic (Plumbing model), CC BY 4.0.", fontsize=7, color=MUTED)
    fig.text(0.01, 0.012, "Gaps < 600 mm, pairs weighted by shared length. Intervals: bootstrap over contexts and pipe pairs; "
             "noise floor: the distance a perfect generator would show at that sample size (verify/compare_sections.py).",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.075, 1, 1))
    fig.savefig(os.path.join(OUT, "04_gaps_vs_buildings.png"), dpi=200)
    plt.close(fig)
    return g["clinic_plumbing"][L]["w1"]


# --- figure 5: how a context is laid out ------------------------------------------

def fig_generation_example(bench, context_id="mep_150"):
    ctx = next(c for c in bench if c["context_id"] == context_id)
    x0, x1, y0, y1 = content_bbox(ctx)
    label_room = 0.62 * (x1 - x0)
    gx0, gx1, gy0, gy1 = x0 - 40, x1 + label_room, y0 - 150, SLAB_MM + 2
    width_in = 5.8
    height_in = min(5.2, max(3.0, width_in * (gy1 - gy0) / (gx1 - gx0) / 0.92))
    fig = plt.figure(figsize=(width_in, height_in))
    ax = fig.add_axes([0.0, 0.0, 1.0, 0.92])
    fit_limits(fig, ax, gx0, gx1, gy0, gy1, None, "top")
    draw_surface(ax, ctx, x0 - 30, x1 + 30, True)
    draw_elements(ax, ctx, True, 6.5)
    names = {0: "row 1: ducts, nearest the slab", 1: "row 2: cable trays and conduits",
             2: "row 3: pipe banks, staggered"}
    for lvl in range(ctx["n_levels"]):
        els = [e for e in ctx["elements"] if e["level"] == lvl]
        top = max(-e["out_mm"] + e["height_mm"] / 2 + e["insulation_mm"] for e in els)
        bot = min(-e["out_mm"] - e["height_mm"] / 2 - e["insulation_mm"] for e in els)
        xb = x1 + 45
        ax.plot([xb, xb], [bot, top], color=MUTED, lw=1.0)
        for yy in (bot, top):
            ax.plot([xb - 12, xb], [yy, yy], color=MUTED, lw=1.0)
        ax.text(xb + 18, (bot + top) / 2, names.get(lvl, f"row {lvl + 1}"), va="center", fontsize=7.5, color=INK)
    order = sorted([i for i, e in enumerate(ctx["elements"]) if e["level"] == 2], key=lambda i: ctx["elements"][i]["along_mm"])
    gaps = cm.neighbour_gaps(ctx)
    k = int(np.argmin(gaps[-(len(order) - 1):]))           # closest pair in the pipe row
    a, b = order[k], order[k + 1]
    g = gaps[-(len(order) - 1):][k]
    row_bottom = min(-e["out_mm"] - e["height_mm"] / 2 - e["insulation_mm"] for e in ctx["elements"] if e["level"] == 2)
    dimension(ax, ctx, a, b, f"{g:.0f} mm clear, drawn from the measured gaps", below=62, fontsize=7.5,
              label_align="left", row_bottom=row_bottom)
    fig.text(0.012, 0.985, f"{ctx['context_id']}, tier {ctx['tier']}: {ctx['n_elements']} elements, {ctx['total_load_kN']:.2f} kN",
             ha="left", va="top", fontsize=9, fontweight="bold", color=INK)
    fig.savefig(os.path.join(OUT, "05_generation_example.png"), dpi=200)
    plt.close(fig)
    return ctx["context_id"]


# --- figure 6: catalog stress test ----------------------------------------------

def fig_catalog_coverage(stress):
    """Left: pipes by nominal size, and which the paper's two-size catalog attaches.
    Right: the best share of pipes any k clamp sizes could attach (exact optimum)."""
    b, d = stress["benchmark"], stress["demand"]
    sizes = list(stress["by_size"])
    tot = [stress["by_size"][k]["pipes"] for k in sizes]
    cov = [stress["by_size"][k]["covered"] for k in sizes]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.4, 4.1), gridspec_kw={"width_ratios": [1.0, 1.0]})
    x = np.arange(len(sizes))
    ax1.bar(x, tot, width=0.62, color=GRID, edgecolor=AXIS, linewidth=0.8, label="no size fits")
    ax1.bar(x, cov, width=0.62, color=BLUE, label="attachable")
    for xi, t, c in zip(x, tot, cov):
        ax1.text(xi, t + 8, "all 293" if c == t and c else f"{t}", ha="center", va="bottom", fontsize=7.5,
                 color=BLUE if c else INK2, fontweight="bold" if c else "normal")
    ax1.set_xticks(x)
    ax1.set_xticklabels(sizes)
    ax1.set_ylim(0, max(tot) * 1.16)
    ax1.set_ylabel("benchmark pipes")
    ax1.yaxis.grid(True)
    ax1.set_axisbelow(True)
    ax1.legend(loc="upper right", ncol=2, bbox_to_anchor=(1.0, 1.04))
    ax1.set_title("Pipe sizes the two-size catalog attaches", loc="left")

    curve = d["curve"]
    ks = [r["k"] for r in curve]
    ax2.plot(ks, [r["pct"] for r in curve], color=BLUE, lw=1.8, marker="o", ms=4.5)
    k2 = next(r["pct"] for r in curve if r["k"] == 2)
    k6 = next(r["pct"] for r in curve if r["k"] == 6)
    ax2.plot([2], [b["pct_pipes"]], marker="D", ms=7, color=ORANGE, ls="none", zorder=5)
    ax2.plot([2, 2], [b["pct_pipes"], k2], color=MUTED, lw=1.0, ls=(0, (3, 2)), zorder=1)
    ax2.text(2.25, b["pct_pipes"], f"the paper's two sizes: {b['pct_pipes']:.1f} %", va="center", fontsize=8, color=ORANGE, fontweight="bold")
    ax2.text(2.25, k2 - 5.0, f"two best-placed sizes: {k2:.1f} %", ha="left", va="center", fontsize=8, color=BLUE, fontweight="bold")
    ax2.text(6.2, k6 - 5.0, f"six sizes: {k6:.0f} %", ha="left", va="center", fontsize=8, color=BLUE, fontweight="bold")
    ax2.text(12.4, 103.0, f"{len(d['diameters'])} distinct diameters, all attached", ha="right", va="bottom", fontsize=8, color=BLUE, fontweight="bold")
    ax2.set_xlim(0.5, 12.5)
    ax2.set_ylim(0, 112)
    ax2.set_xticks(ks)
    ax2.set_xlabel(f"number of clamp sizes, each fitting a {d['width_mm']:g} mm diameter window")
    ax2.set_ylabel("benchmark pipes attachable (%)")
    ax2.yaxis.grid(True)
    ax2.set_axisbelow(True)
    ax2.set_title("What the dataset asks of any catalog", loc="left")
    fig.suptitle(f"A two-size clamp catalog attaches {b['pct_pipes']:.1f} % of pipes (95 % CI {b['ci'][0]:.1f}-{b['ci'][1]:.1f}), all of them DN40",
                 x=0.012, ha="left", fontsize=11, fontweight="bold", color=INK, y=0.985)
    fig.text(0.012, 0.045, f"Benchmark: {b['pipes']:,} pipes. Bins 48-54 mm (2.5 kN) and 108-114 mm (4.0 kN); attach diameter = insulated OD for cold lines, bare OD otherwise. "
             f"The heaviest pipe is {b['max_pipe_load_kN']:.2f} kN, so load never binds.", fontsize=7, color=MUTED)
    fig.text(0.012, 0.012, f"{b['not_pipe']:,} of the {b['elements']:,} elements are trays, ducts or conduits, for which a pipe-clamp catalog defines no attachment. "
             "Interval: cluster bootstrap over contexts (verify/catalog_stress.py).", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.07, 1, 0.96))
    fig.savefig(os.path.join(OUT, "06_catalog_coverage.png"), dpi=200)
    plt.close(fig)
    return b["pct_pipes"]


# --- title art: a congested section drawn light-on-transparent for a dark slide --

def fig_title_art(bench):
    ctx = next(c for c in bench if c["tier"] == "C8" and c["surface"]["kind"] == "ceiling" and c["n_levels"] == 3
               and len({e["trade"] for e in c["elements"]}) >= 3)
    fig = plt.figure(figsize=(6.4, 4.0))
    ax = fig.add_axes([0, 0, 1, 1])
    x0, x1, y0, y1 = content_bbox(ctx)
    fit_limits(fig, ax, x0 - 40, x1 + 40, y0 - 40, SLAB_MM + 2)
    xl = ax.get_xlim()
    ax.add_patch(Rectangle((xl[0], 0), xl[1] - xl[0], SLAB_MM, fc="none", ec="#CADCFC", lw=0.8, hatch="////", alpha=0.5, zorder=0))
    saved = dict(TRADE_COLOR)
    TRADE_COLOR.update({t: "#CADCFC" for t in TRADE_COLOR})     # one light ink; identity by shape only
    try:
        draw_elements(ax, ctx, label_elements=False)
    finally:
        TRADE_COLOR.update(saved)
    fig.savefig(os.path.join(OUT, "title_art.png"), dpi=200, transparent=True)
    plt.close(fig)
    return ctx["context_id"]


# --- numbers the slide deck reads (docs/deck/build_deck.js) ---------------------

def write_deck_data(splits, stress, trends, sections):
    bench = splits["benchmark"]
    cg = _compare_gaps_module()
    mep = np.array(json.load(open(cg.MEASURED_MEP)))
    pl = np.array(json.load(open(cg.MEASURED_PLUMBING)))
    r = cg.compare(bench, mep, pl, "4.0")
    tiers = [f"C{n}" for n in range(1, 9)]
    summ = cm.tier_summary(bench)
    kinds, dn, trades, surf = Counter(), Counter(), Counter(), Counter()
    for data in splits.values():
        for c in data:
            surf[c["surface"]["kind"]] += 1
            for e in c["elements"]:
                kinds[e["kind"]] += 1
                trades[e["trade"]] += 1
                if e["kind"] == "pipe":
                    dn[int(e["label"][2:])] += 1
    data = {
        "tiers": tiers,
        "splits": {s: {"contexts": len(d), "elements": sum(c["n_elements"] for c in d),
                       "seed": CANONICAL_SPLITS[s]["seed"]} for s, d in splits.items()},
        "composition": {"kinds": dict(kinds), "dn": {f"DN{k}": dn[k] for k in sorted(dn)},
                        "trades": dict(trades), "contexts": sum(surf.values()),
                        "elements": sum(kinds.values()),
                        "ceiling_pct": 100.0 * surf["ceiling"] / sum(surf.values())},
        "tier_medians": {t: {"clear_gap_mm": summ[t]["clear_gap_mm"], "load_kN": summ[t]["load_kN"],
                             "bundle_width_mm": summ[t]["bundle_width_mm"]} for t in tiers},
        "catalog": stress, "trends": trends, "sections": sections, "kind_totals_benchmark": cm.kind_totals(bench),
        "w1": {"insulation": r["w1"]["insulation"], "bare": r["w1"]["bare"],
               "real_to_real": r["baselines"]["real_to_real"],
               "fixed_floor_gap": r["baselines"]["fixed_floor_gap_to_mep"]},
        "measured": r["measured"], "fit": dict(r["fit"]),
    }
    c2 = [c for c in bench if c["tier"] == "C2" and c["surface"]["kind"] == "ceiling"]
    data["example_record"] = next(
        (c for c in c2 if any(e["insulation_mm"] > 0 for e in c["elements"])
         and {e["kind"] for e in c["elements"]} == {"pipe", "cable_tray"}), c2[0])
    with open(os.path.join(OUT, "deck_data.json"), "w") as f:
        json.dump(data, f, indent=1)


def write_qr(url="https://github.com/lavinia-ped/CrossMEP_Dataset"):
    try:
        import qrcode
    except ImportError:
        print("qrcode not installed; skipping QR (pip install qrcode[pil])")
        return
    qrcode.make(url, box_size=10, border=2).save(os.path.join(OUT, "qr_repo.png"))


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    splits = {s: cm.load(s) for s in SPLITS}
    bench = splits["benchmark"]
    print("01:", fig_what_a_context_is(bench))
    print("02:", fig_tier_gallery(bench))
    trends = _verify_module("tier_trends").run(bench)
    fig_tier_stats(bench, trends)
    cs = _verify_module("compare_sections")
    sections = cs.compare(bench)
    sections["sensitivity"] = cs.sensitivity(bench)
    print("04: W1 generated -> clinic (mm)", round(fig_gaps_vs_buildings(bench, sections), 1))
    print("05:", fig_generation_example(bench))
    stress = _verify_module("catalog_stress").stress_test(catalog.PAPER_CATALOG, splits=splits)
    print("06: attachable pipes (%)", round(fig_catalog_coverage(stress), 1))
    print("title art:", fig_title_art(bench))
    write_deck_data(splits, stress, trends, sections)
    write_qr()
    print("wrote", sorted(os.listdir(OUT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

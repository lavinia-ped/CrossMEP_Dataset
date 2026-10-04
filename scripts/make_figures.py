#!/usr/bin/env python3
"""Regenerate the presentation figures in docs/figures/ from the released data.

    pip install matplotlib
    python scripts/make_figures.py            # writes docs/figures/*.png and prints the context ids used

Figures (all from data/v4.0 unless stated; 16:9-friendly, 200 dpi):

    01_what_a_context_is.png   one C5 ceiling section with its fields called out
    02_tiers_examples.png      representative C1 / C4 / C8 sections (one scale per panel)
    03_tiers_stats.png         per-tier minimum clear gap and total load (benchmark)
    04_gaps_vs_measured.png    generated clear gaps vs the Duplex Apartment measurement,
                               with the lognormal fit and the Wasserstein-1 distances
    05_v3_vs_v4.png            the same context in revision 3.0 and 4.0 geometry (same scale)
    06_catalog_coverage.png    share of pipes a two-bin clamp catalog covers, per tier

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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import crossmep.tasks as cm  # noqa: E402
from crossmep.layout import GAP_CAP_MM, GAP_LOGNORMAL_MU, GAP_LOGNORMAL_SIGMA  # noqa: E402

OUT = os.path.join(ROOT, "docs", "figures")

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


def _compare_gaps_module():
    spec = importlib.util.spec_from_file_location("compare_gaps", os.path.join(ROOT, "verify", "compare_gaps.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- drawing a context ----------------------------------------------------------

def content_bbox(ctx):
    """(x0, x1, y0, y1) of the drawn elements in screen mm (ceiling: x = along, y = -out)."""
    sk = ctx["surface"]["kind"]
    xs, ys = [], []
    for e in ctx["elements"]:
        cx, cy = (e["along_mm"], -e["out_mm"]) if sk == "ceiling" else (e["out_mm"], -e["along_mm"])
        w, h, ins = e["width_mm"], e["height_mm"], e["insulation_mm"]
        xs += [cx - w / 2 - ins, cx + w / 2 + ins]
        ys += [cy - h / 2 - ins, cy + h / 2 + ins]
    return min(xs), max(xs), min(ys), max(ys)


def draw_elements(ax, ctx, label_elements=True):
    sk = ctx["surface"]["kind"]
    for e in ctx["elements"]:
        cx, cy = (e["along_mm"], -e["out_mm"]) if sk == "ceiling" else (e["out_mm"], -e["along_mm"])
        w, h, ins = e["width_mm"], e["height_mm"], e["insulation_mm"]
        col = TRADE_COLOR[e["trade"]]
        if e["shape"] == "round":
            if ins > 0:
                ax.add_patch(Circle((cx, cy), w / 2 + ins, fill=False, ec=col, lw=0.8, ls=(0, (2, 2)), alpha=0.7))
            ax.add_patch(Circle((cx, cy), w / 2, fill=False, ec=col, lw=1.6))
            if label_elements:
                ax.text(cx, cy - w / 2 - ins - 12, e["label"], ha="center", va="top", fontsize=6.5, color=INK2)
        else:
            ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fill=True, fc=col, alpha=0.08, ec=col, lw=1.6))
            if label_elements:
                ax.text(cx, cy, e["label"], ha="center", va="center", fontsize=6.5, color=INK2)


def draw_surface(ax, ctx, x0, x1):
    s = ctx["surface"]
    ax.add_patch(Rectangle((x0, 0), x1 - x0, SLAB_MM, fc="#efeeea", ec=AXIS, lw=0.8, hatch="////", zorder=0))
    ax.text(x0 + 10, SLAB_MM / 2, f"{'slab' if s['kind'] == 'ceiling' else 'wall'} · {s['substrate']} · {s['thickness_mm']:.0f} mm",
            va="center", fontsize=6.5, color=INK2, bbox=dict(fc=SURFACE, ec="none", pad=1.2))


def fit_limits(fig, ax, x0, x1, y0, y1, scale=None, anchor_top=True):
    """Set limits so the content fits the axes box at an explicit mm-per-inch
    scale (the max needed, unless given), keeping aspect equal without letting
    matplotlib resize the box.  Returns the scale used."""
    pos = ax.get_position()
    fw, fh = fig.get_size_inches()
    bw, bh = pos.width * fw, pos.height * fh
    need = max((x1 - x0) / bw, (y1 - y0) / bh)
    s = need if scale is None else max(scale, need)
    cx = (x0 + x1) / 2
    ax.set_xlim(cx - s * bw / 2, cx + s * bw / 2)
    if anchor_top:
        ax.set_ylim(y1 - s * bh, y1)
    else:
        cy = (y0 + y1) / 2
        ax.set_ylim(cy - s * bh / 2, cy + s * bh / 2)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return s


def draw_context(fig, ax, ctx, title=None, scale=None, min_width=600.0, label_elements=True):
    x0, x1, y0, y1 = content_bbox(ctx)
    width = max(x1 - x0, min_width)
    cx = (x0 + x1) / 2
    gx0, gx1 = cx - width / 2 - 30, cx + width / 2 + 30
    gy0, gy1 = y0 - 40, SLAB_MM + 2
    s = fit_limits(fig, ax, gx0, gx1, gy0, gy1, scale)
    xl = ax.get_xlim()
    draw_surface(ax, ctx, xl[0] + 0.01 * (xl[1] - xl[0]), xl[1] - 0.01 * (xl[1] - xl[0]))
    draw_elements(ax, ctx, label_elements)
    if title:
        ax.set_title(title, loc="left", fontsize=9)
    return s


def dimension(ax, ctx, a, b, label):
    """Dimension line between the insulation surfaces of elements a and b (ceiling frame)."""
    ea, eb = ctx["elements"][a], ctx["elements"][b]
    xa = ea["along_mm"] + ea["width_mm"] / 2 + ea["insulation_mm"]
    xb = eb["along_mm"] - eb["width_mm"] / 2 - eb["insulation_mm"]
    bottom = min(-e["out_mm"] - e["height_mm"] / 2 - e["insulation_mm"] for e in (ea, eb))
    y = bottom - 30
    ax.annotate("", xy=(xa, y), xytext=(xb, y), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
    for x in (xa, xb):
        ax.plot([x, x], [y - 6, bottom], color=INK, lw=0.5, alpha=0.6)
    ax.text((xa + xb) / 2, y - 10, label, ha="center", va="top", fontsize=7.5, color=INK, fontweight="bold")


def trade_legend(fig, trades, y=0.03):
    handles = [plt.Line2D([], [], color=TRADE_COLOR[t], lw=1.8, label=TRADE_NAME[t]) for t in trades]
    fig.legend(handles=handles, loc="lower center", ncol=len(trades), bbox_to_anchor=(0.5, y), handlelength=1.6)


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
    trade_legend(fig, sorted({e["trade"] for e in ctx["elements"]}), y=0.02)
    fig.savefig(os.path.join(OUT, "01_what_a_context_is.png"), dpi=200)
    plt.close(fig)
    return ctx["context_id"]


# --- figure 2: tier examples ----------------------------------------------------

def fig_tier_examples(bench):
    pick = {}
    for tier, want in (("C1", lambda c: c["elements"][0]["kind"] == "pipe"),
                       ("C4", lambda c: len({e["kind"] for e in c["elements"]}) >= 2),
                       ("C8", lambda c: c["n_levels"] == 3 and len({e["trade"] for e in c["elements"]}) >= 3)):
        pick[tier] = next(c for c in bench if c["tier"] == tier and c["surface"]["kind"] == "ceiling" and want(c))
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), gridspec_kw=dict(width_ratios=[1, 1.5, 2.4]))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.14, wspace=0.08)
    for ax, (tier, ctx) in zip(axes, pick.items()):
        draw_context(fig, ax, ctx, title=f"{tier} - {ctx['n_elements']} element{'s' if ctx['n_elements'] > 1 else ''}, "
                                         f"{ctx['n_levels']} row{'s' if ctx['n_levels'] > 1 else ''}, {ctx['total_load_kN']:.2f} kN")
    trades = sorted({e["trade"] for c in pick.values() for e in c["elements"]})
    trade_legend(fig, trades)
    fig.savefig(os.path.join(OUT, "02_tiers_examples.png"), dpi=200)
    plt.close(fig)
    return {t: c["context_id"] for t, c in pick.items()}


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


def fig_tier_stats(bench):
    tiers = [f"C{n}" for n in range(1, 9)]
    gaps = [[cm.min_clear_gap(c) for c in bench if c["tier"] == t and c["n_elements"] > 1] for t in tiers[1:]]
    loads = [[c["total_load_kN"] for c in bench if c["tier"] == t] for t in tiers]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
    _box(a, gaps, tiers[1:], BLUE, "minimum clear gap between elements (mm)",
         "Tighter: median clear gap 120 mm (C2) to 62 mm (C8)", "{:.0f}")
    _box(b, loads, tiers, BLUE, "total load at the support (kN)",
         "Heavier: median load 0.10 kN (C1) to 1.71 kN (C8)", "{:.2f}")
    a.set_ylim(0, 450)
    b.set_ylim(0, 6.5)
    fig.text(0.01, 0.01, "Benchmark split, 125 contexts per tier; boxes = interquartile range, line = median, whiskers = 1.5 IQR.",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(OUT, "03_tiers_stats.png"), dpi=200)
    plt.close(fig)


# --- figure 4: gaps vs measured --------------------------------------------------

def fig_gaps_vs_measured(bench, bench_v3):
    cg = _compare_gaps_module()
    mep = np.array(json.load(open(cg.MEASURED_MEP)))
    pl = np.array(json.load(open(cg.MEASURED_PLUMBING)))
    r4 = cg.compare(bench, mep, pl, "4.0")
    r3 = cg.compare(bench_v3, mep, pl, "3.0")
    m6 = mep[mep < 600]
    g4 = np.array([v for c in bench for v in cm.neighbour_gaps(c, "insulation")])
    g3 = np.array([v for c in bench_v3 for v in cm.neighbour_gaps(c, "insulation")])
    bins = np.arange(0, 601, 25)
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.hist(m6, bins=bins, density=True, color=BLUE, alpha=0.55, label=f"measured, Duplex Apartment MEP model (n = {len(m6)})")
    ax.hist(g4[g4 < 600], bins=bins, density=True, histtype="step", color=ORANGE, lw=2.0,
            label=f"generated, revision 4.0 (n = {np.sum(g4 < 600):,})")
    ax.hist(g3[g3 < 600], bins=bins, density=True, histtype="step", color=AQUA, lw=2.0,
            label=f"generated, revision 3.0 - the paper's files (n = {np.sum(g3 < 600):,})")
    x = np.linspace(25, 600, 400)
    pdf = np.exp(-(np.log(x) - GAP_LOGNORMAL_MU) ** 2 / (2 * GAP_LOGNORMAL_SIGMA ** 2)) / (x * GAP_LOGNORMAL_SIGMA * np.sqrt(2 * np.pi))
    ax.plot(x, pdf, color=INK, lw=1.2, ls=(0, (4, 3)), label="lognormal fitted to the measurement (mu 5.018, sigma 0.848)")
    ax.set_xlabel("clear gap between adjacent runs, surface to surface (mm)")
    ax.set_ylabel("density")
    ax.set_xlim(0, 600)
    ax.set_ylim(0, 0.0115)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right")
    w4, w3 = r4["w1"]["insulation"]["mep"], r3["w1"]["insulation"]["mep"]
    ax.text(0.50, 0.60, f"Wasserstein-1 distance to the measurement\n  revision 4.0: {w4:.0f} mm\n  revision 3.0: {w3:.0f} mm\n"
            f"  the two real discipline models: {r4['baselines']['real_to_real']:.0f} mm apart\n"
            f"  a fixed 25 mm modular gap: {r4['baselines']['fixed_floor_gap_to_mep']:.0f} mm",
            transform=ax.transAxes, ha="left", va="top", fontsize=8, color=INK2)
    ax.set_title("Generated spacing matches a built project; revision 4.0 removed a 50 mm offset", loc="left")
    fig.text(0.01, 0.01, f"Spikes at {GAP_CAP_MM:.0f} mm (4.0) and {GAP_CAP_MM + 50:.0f} mm (3.0) are the generator's gap cap; "
             f"{100 * np.mean(m6 < 25):.0f} % of the measured gaps lie below the 25 mm floor the generator applies.",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(OUT, "04_gaps_vs_measured.png"), dpi=200)
    plt.close(fig)
    return w4, w3


# --- figure 5: v3 vs v4 ----------------------------------------------------------

def fig_v3_vs_v4(bench, bench_v3):
    idx = next(i for i, c in enumerate(bench) if c["tier"] == "C4" and c["surface"]["kind"] == "ceiling"
               and c["n_levels"] == 1 and all(e["kind"] == "pipe" for e in c["elements"]))
    c4, c3 = bench[idx], bench_v3[idx]
    order = sorted(range(len(c4["elements"])), key=lambda i: c4["elements"][i]["along_mm"])
    k = int(np.argmin(cm.neighbour_gaps(c4)))
    a, b = order[k], order[k + 1]
    g4, g3 = cm.neighbour_gaps(c4)[k], cm.neighbour_gaps(c3)[k]
    fig, axes = plt.subplots(1, 2, figsize=(10, 2.9))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.12, wspace=0.05)
    # common scale: the wider (3.0) context decides
    scale = None
    for ax, ctx in ((axes[0], c3), (axes[1], c4)):
        x0, x1, y0, y1 = content_bbox(ctx)
        pos = ax.get_position()
        fw, fh = fig.get_size_inches()
        need = max((x1 - x0 + 60) / (pos.width * fw), (SLAB_MM + 2 - (y0 - 90)) / (pos.height * fh))
        scale = need if scale is None else max(scale, need)
    for ax, ctx, g, title in ((axes[0], c3, g3, "revision 3.0 (the paper's files): sampled gap + 50 mm envelope"),
                              (axes[1], c4, g4, "revision 4.0: the sampled gap is the clear gap")):
        x0, x1, y0, y1 = content_bbox(ctx)
        fit_limits(fig, ax, x0 - 30, x1 + 30, y0 - 90, SLAB_MM + 2, scale=scale)
        xl = ax.get_xlim()
        draw_surface(ax, ctx, xl[0] + 0.01 * (xl[1] - xl[0]), xl[1] - 0.01 * (xl[1] - xl[0]))
        draw_elements(ax, ctx)
        dimension(ax, ctx, a, b, f"{g:.0f} mm clear")
        ax.set_title(title, loc="left", fontsize=9)
    fig.text(0.01, 0.02, f"Same context ({c4['context_id']}), same elements and loads; only the spacing moved. "
             f"Bundle width {c3['bundle_width_mm']:.0f} -> {c4['bundle_width_mm']:.0f} mm; "
             f"closest pair {g3:.0f} -> {g4:.0f} mm.", fontsize=7.5, color=INK2)
    fig.savefig(os.path.join(OUT, "05_v3_vs_v4.png"), dpi=200)
    plt.close(fig)
    return c4["context_id"]


# --- figure 6: catalog coverage --------------------------------------------------

def fig_catalog_coverage(bench):
    bins = [(48.0, 54.0, 2.5), (108.0, 114.0, 4.0)]
    cov = cm.catalog_coverage(bench, bins)
    tiers = [f"C{n}" for n in range(1, 9)]
    vals = [cov[t] for t in tiers]
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    ax.bar(tiers, vals, width=0.34, color=BLUE)
    ax.axhline(cov["overall"], color=INK, lw=1.0)
    ax.text(-0.45, cov["overall"] + 0.7, f"overall {cov['overall']:.1f} %", ha="left", fontsize=8, color=INK)
    ax.set_xlim(-0.6, 7.6)
    ax.set_ylim(0, 25)
    ax.set_ylabel("pipes the catalog can attach (%)")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_title("A two-bin clamp catalog attaches 1 pipe in 9 - and no tray, duct or conduit", loc="left")
    fig.text(0.01, 0.035, "Bins: 48-54 mm at 2.5 kN and 108-114 mm at 4.0 kN, tested on the bare OD for hot/bare lines and the insulated OD for cold lines.",
             fontsize=7, color=MUTED)
    fig.text(0.01, 0.005, f"{cov['non_pipe_elements']:,} of the 4,500 benchmark elements are trays, ducts or conduits, for which a clamp catalog defines no attachment.",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(os.path.join(OUT, "06_catalog_coverage.png"), dpi=200)
    plt.close(fig)
    return cov["overall"]


# --- title art: a congested section drawn light-on-transparent for a dark slide --

def fig_title_art(bench):
    ctx = next(c for c in bench if c["tier"] == "C8" and c["surface"]["kind"] == "ceiling" and c["n_levels"] == 3
               and len({e["trade"] for e in c["elements"]}) >= 3)
    light = {t: "#CADCFC" for t in TRADE_COLOR}           # one light ink, identity by shape only
    fig = plt.figure(figsize=(6.4, 4.0))
    ax = fig.add_axes([0, 0, 1, 1])
    x0, x1, y0, y1 = content_bbox(ctx)
    fit_limits(fig, ax, x0 - 40, x1 + 40, y0 - 40, SLAB_MM + 2)
    xl = ax.get_xlim()
    ax.add_patch(Rectangle((xl[0], 0), xl[1] - xl[0], SLAB_MM, fc="none", ec="#CADCFC", lw=0.8, hatch="////", alpha=0.5, zorder=0))
    saved = dict(TRADE_COLOR)
    TRADE_COLOR.update(light)
    try:
        draw_elements(ax, ctx, label_elements=False)
    finally:
        TRADE_COLOR.update(saved)
    fig.savefig(os.path.join(OUT, "title_art.png"), dpi=200, transparent=True)
    plt.close(fig)
    return ctx["context_id"]


# --- numbers the slide deck reads (docs/deck/build_deck.js) ---------------------

def write_deck_data(bench, bench_v3):
    cg = _compare_gaps_module()
    mep = np.array(json.load(open(cg.MEASURED_MEP)))
    pl = np.array(json.load(open(cg.MEASURED_PLUMBING)))
    r4 = cg.compare(bench, mep, pl, "4.0")
    r3 = cg.compare(bench_v3, mep, pl, "3.0")
    cov = cm.catalog_coverage(bench, [(48.0, 54.0, 2.5), (108.0, 114.0, 4.0)])
    tiers = [f"C{n}" for n in range(1, 9)]
    summ = cm.tier_summary(bench)
    data = {
        "tiers": tiers,
        "tier_medians": {t: {"clear_gap_mm": summ[t]["clear_gap_mm"], "load_kN": summ[t]["load_kN"],
                             "bundle_width_mm": summ[t]["bundle_width_mm"]} for t in tiers},
        "coverage_pct": {t: cov[t] for t in tiers}, "coverage_overall_pct": cov["overall"],
        "non_pipe_elements": cov["non_pipe_elements"], "kind_totals": cm.kind_totals(bench),
        "w1": {"v4_insulation": r4["w1"]["insulation"], "v4_bare": r4["w1"]["bare"],
               "v3_envelope": r3["w1"]["envelope"], "v3_insulation": r3["w1"]["insulation"],
               "real_to_real": r4["baselines"]["real_to_real"],
               "fixed_floor_gap": r4["baselines"]["fixed_floor_gap_to_mep"]},
        "measured": r4["measured"], "fit": {k: v for k, v in r4["fit"].items()},
        "share_measured_below_75": r4["baselines"]["share_measured_mep_below_75mm"],
        "min_insulation_gap_v3": r3["generated"]["insulation"]["min"],
    }
    with open(os.path.join(OUT, "deck_data.json"), "w") as f:
        json.dump(data, f, indent=1)


def write_qr(url="https://github.com/lavinia-ped/CrossMEP_Dataset"):
    try:
        import qrcode
    except ImportError:
        print("qrcode not installed; skipping QR (pip install qrcode[pil])")
        return
    img = qrcode.make(url, box_size=10, border=2)
    img.save(os.path.join(OUT, "qr_repo.png"))


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    bench, bench_v3 = cm.load("benchmark"), cm.load("benchmark", "3.0")
    print("01:", fig_what_a_context_is(bench))
    print("02:", fig_tier_examples(bench))
    fig_tier_stats(bench)
    print("04: W1 v4 / v3 =", fig_gaps_vs_measured(bench, bench_v3))
    print("05:", fig_v3_vs_v4(bench, bench_v3))
    print("06: overall coverage", fig_catalog_coverage(bench))
    print("title art:", fig_title_art(bench))
    write_deck_data(bench, bench_v3)
    write_qr()
    print("wrote", sorted(os.listdir(OUT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

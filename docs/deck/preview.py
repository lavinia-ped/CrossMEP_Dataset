#!/usr/bin/env python3
"""Render a trace of build_deck.js to PNG previews for visual QA when LibreOffice
is unavailable.

    DECK_TRACE=/tmp/trace.json node docs/deck/build_deck.js
    python docs/deck/preview.py /tmp/trace.json /tmp/previews

Shapes, images and tables are drawn to scale; text is wrapped with
metric-conservative substitutes (Liberation Sans for Calibri, Liberation Serif
scaled up for Cambria), so a box that fits here fits in PowerPoint.  Boxes whose
wrapped text exceeds their height are outlined in red and listed on stderr.
Charts are drawn as labelled frames.
"""
from __future__ import annotations

import base64
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

PX = 110                                  # pixels per inch
FONT_DIR = "/usr/share/fonts/truetype/liberation"
FACES = {
    ("sans", False): ("LiberationSans-Regular.ttf", 1.0),
    ("sans", True): ("LiberationSans-Bold.ttf", 1.0),
    ("serif", False): ("LiberationSerif-Regular.ttf", 1.12),     # Cambria is wider than Liberation Serif
    ("serif", True): ("LiberationSerif-Bold.ttf", 1.12),
    ("mono", False): ("LiberationMono-Regular.ttf", 1.0),
    ("mono", True): ("LiberationMono-Bold.ttf", 1.0),
}
SCHEME = {"tx1": "dk1", "tx2": "dk2", "bg1": "lt1", "bg2": "lt2", "accent1": "accent1", "accent2": "accent2",
          "accent3": "accent3", "accent4": "accent4", "accent5": "accent5", "accent6": "accent6"}


def rgb(color, theme, default="000000"):
    if not color:
        color = default
    if color in SCHEME:
        color = theme["colors"][SCHEME[color]]
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def font(face, bold, pt):
    name, scale = FACES[(face, bold)]
    return ImageFont.truetype(os.path.join(FONT_DIR, name), max(1, int(round(pt * PX / 72 * scale))))


def wrap(text, fnt, width_px):
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(" "), ""
        for w in words:
            cand = (cur + " " + w).strip()
            if fnt.getlength(cand) <= width_px or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def draw_text(img, d, theme, box, runs, opts, face_default="sans"):
    """runs: list of (text, run_opts). Returns True if the text overflowed."""
    x, y, w, h = [float(box[k]) * PX for k in ("x", "y", "w", "h")]
    margin = opts.get("margin", 0.1)
    if isinstance(margin, (int, float)):
        m = margin * PX / 72 * (72 / 100) if margin <= 1 else margin * PX / 72   # pptxgenjs margin is in points-ish; inset ~0.1 in default
        mx = my = (0.1 * PX if opts.get("margin") is None else float(opts.get("margin") or 0) * PX)
    else:
        mx = my = 0.1 * PX
    align = opts.get("align", "left")
    valign = opts.get("valign", "top")
    base_size = float(opts.get("fontSize", 14))
    paragraphs = []                                   # list of (lines, fnt, color, pt, bullet, space_after)
    cur_runs = []
    for text, ro in runs:
        cur_runs.append((text, ro))
        if ro.get("breakLine"):
            paragraphs.append(cur_runs)
            cur_runs = []
    if cur_runs:
        paragraphs.append(cur_runs)
    lines_out = []                                    # (fnt, color, line, indent, space_after)
    for para in paragraphs:
        # a paragraph may contain runs of different size; wrap on the first run's font, concatenate text
        text = "".join(t for t, _ in para)
        ro = para[0][1]
        pt = float(ro.get("fontSize", base_size))
        bold = bool(ro.get("bold", opts.get("bold", False)))
        face = face_default
        if ro.get("fontFace") or opts.get("fontFace"):
            ff = (ro.get("fontFace") or opts.get("fontFace")).lower()
            face = "mono" if "mono" in ff else ("serif" if ff in ("cambria", "georgia", "times new roman") else "sans")
        fnt = font(face, bold, pt)
        col = rgb(ro.get("color", opts.get("color")), theme)
        bullet = bool(ro.get("bullet"))
        indent = fnt.getlength("•  ") if bullet else 0
        wrapped = wrap(text, fnt, w - 2 * mx - indent)
        for i, ln in enumerate(wrapped):
            lines_out.append((fnt, col, ("•  " if bullet and i == 0 else ""), ln, indent if i > 0 else 0, pt))
        sa = float(ro.get("paraSpaceAfter", 0)) * PX / 72
        if lines_out:
            lines_out[-1] = lines_out[-1] + (sa,)
    heights = [f.size * 1.2 + (ln[6] if len(ln) > 6 else 0) for ln in lines_out for f in [ln[0]]]
    total = sum(heights)
    overflow = total > h - 2 * my + 1
    yy = y + my
    if valign == "middle":
        yy = y + (h - total) / 2
    elif valign == "bottom":
        yy = y + h - my - total
    for ln, lh in zip(lines_out, heights):
        fnt, col, prefix, text, indent, pt = ln[:6]
        s = prefix + text
        tw = fnt.getlength(s)
        xx = x + mx + indent
        if align == "center":
            xx = x + (w - tw) / 2
        elif align == "right":
            xx = x + w - mx - tw
        d.text((xx, yy), s, font=fnt, fill=col)
        yy += lh
    if overflow:
        d.rectangle([x, y, x + w, y + h], outline=(220, 0, 0), width=3)
    return overflow


def render(trace, outdir):
    os.makedirs(outdir, exist_ok=True)
    theme = trace["theme"]
    W, H = int(trace["size"][0] * PX), int(trace["size"][1] * PX)
    problems = []
    for n, sl in enumerate(trace["slides"], start=1):
        layout = trace["layouts"][sl["layout"]]
        img = Image.new("RGB", (W, H), rgb(layout.get("background", {}).get("color", "FFFFFF"), theme))
        d = ImageDraw.Draw(img)
        placeholders = {}
        for obj in layout.get("objects", []):
            if "placeholder" in obj:
                o = obj["placeholder"]["options"]
                placeholders[o["name"]] = o
            elif "text" in obj:
                o = obj["text"]["options"]
                draw_text(img, d, theme, o, [(obj["text"]["text"], {})], o)
        if layout.get("slideNumber"):
            o = layout["slideNumber"]
            draw_text(img, d, theme, o, [(str(n), {})], o)
        for it in sl["items"]:
            m, args = it["m"], it["args"]
            if m == "addShape":
                o = args[1]
                x, y, w, h = [float(o[k]) * PX for k in ("x", "y", "w", "h")]
                fill = o.get("fill", {}).get("color")
                r = int(float(o.get("rectRadius", 0)) * PX)
                if args[0] == "ellipse":
                    d.ellipse([x, y, x + w, y + h], fill=rgb(fill, theme) if fill else None)
                else:
                    d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=rgb(fill, theme) if fill else None)
            elif m == "addImage":
                o = args[0]
                x, y, w, h = [float(o[k]) * PX for k in ("x", "y", "w", "h")]
                if o.get("path") and os.path.exists(o["path"]):
                    im = Image.open(o["path"]).convert("RGBA").resize((max(1, int(w)), max(1, int(h))))
                    img.paste(im, (int(x), int(y)), im)
                else:
                    d.rectangle([x, y, x + w, y + h], outline=(120, 120, 120), width=2)
            elif m == "addChart":
                o = args[2]
                x, y, w, h = [float(o[k]) * PX for k in ("x", "y", "w", "h")]
                d.rectangle([x, y, x + w, y + h], outline=(42, 120, 214), width=2)
                d.text((x + 10, y + 10), "CHART: " + str(o.get("title", "")), font=font("sans", False, 12), fill=(42, 120, 214))
            elif m == "addTable":
                rows, o = args[0], args[1]
                x, y = float(o["x"]) * PX, float(o["y"]) * PX
                colw = [float(c) * PX for c in o["colW"]]
                rh = o.get("rowH", 0.4)
                rhs = rh if isinstance(rh, list) else [rh] * len(rows)
                fs = float(o.get("fontSize", 12))
                for row, rh_in in zip(rows, rhs):
                    rhp = float(rh_in) * PX
                    xx = x
                    for cell, cw in zip(row, colw):
                        co = cell.get("options", {})
                        fill = co.get("fill", {}).get("color") if isinstance(co.get("fill"), dict) else None
                        d.rectangle([xx, y, xx + cw, y + rhp], fill=rgb(fill, theme) if fill else None, outline=(200, 200, 200))
                        over = draw_text(img, d, theme, {"x": xx / PX, "y": y / PX, "w": cw / PX, "h": rhp / PX},
                                         [(cell["text"], co)], {"fontSize": co.get("fontSize", fs), "color": co.get("color"),
                                                               "align": co.get("align", "left"), "valign": "middle", "margin": 0.07})
                        if over:
                            problems.append(f"slide {n}: table cell overflow: {cell['text'][:40]!r}")
                        xx += cw
                    y += rhp
            elif m == "addText":
                text, o = args[0], args[1]
                face = "sans"
                if "placeholder" in o:
                    po = dict(placeholders[o["placeholder"]])
                    face = "serif" if po.get("type") == "title" else "sans"
                    box, opts = po, {**po, **{k: v for k, v in o.items() if k != "placeholder"}}
                else:
                    box, opts = o, o
                runs = [(text, {})] if isinstance(text, str) else [(r["text"], r.get("options", {})) for r in text]
                if draw_text(img, d, theme, box, runs, opts, face):
                    first = runs[0][0] if runs else ""
                    problems.append(f"slide {n}: text overflow in {o.get('objectName') or o.get('placeholder')}: {first[:50]!r}")
        img.save(os.path.join(outdir, f"slide-{n:02d}.png"))
    for p in problems:
        print(p, file=sys.stderr)
    print(f"rendered {len(trace['slides'])} slides -> {outdir}; {len(problems)} overflow warnings")
    return 0


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        tr = json.load(f)
    sys.exit(render(tr, sys.argv[2]))

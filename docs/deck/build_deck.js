#!/usr/bin/env node
/* Build the ten-minute CIB W78 talk on CrossMEP as a PowerPoint file.

   Inputs:  docs/figures/*.png and docs/figures/deck_data.json, both written by
            scripts/make_figures.py from the released data (with the QR codes of
            the repository and the hosted studio); the gallery screenshot from
            scripts/screenshot_gallery.js; the Generator Studio screenshots
            (08_studio_demo) from
            scripts/screenshot_studio.js.
   Output:  docs/CrossMEP_CIBW78_talk.pptx (speaker notes = docs/TALK.md)

   Rebuild:
       pip install matplotlib "qrcode[pil]" && python scripts/make_figures.py
       NODE_PATH=$(npm root -g) node scripts/screenshot_gallery.js        # needs Playwright
       NODE_PATH=$(npm root -g) node scripts/screenshot_studio.js         # needs Playwright
       npm install pptxgenjs react-icons react react-dom sharp jszip      # anywhere; set NODE_PATH to it
       node docs/deck/build_deck.js

   The deck is a structured one (theme, named layouts with placeholders,
   sections, speaker notes) so it can be restyled in PowerPoint; the scheme
   colours are written into the theme after pptxgenjs saves the file.
   DECK_TRACE=<file> also writes a trace of every drawing call, which
   docs/deck/preview.py renders for layout checks without LibreOffice.
*/
"use strict";
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

let sharp = null, icons = null, React = null, ReactDOMServer = null;
try {
  sharp = require("sharp");
  icons = require("react-icons/fi");
  React = require("react");
  ReactDOMServer = require("react-dom/server");
} catch (e) {
  console.warn("icons unavailable (" + e.message + "); using numbered circles");
}

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = path.join(ROOT, "docs", "figures");
const OUT = path.join(ROOT, "docs", "CrossMEP_CIBW78_talk.pptx");
const D = JSON.parse(fs.readFileSync(path.join(FIG, "deck_data.json"), "utf8"));
const REPO = "github.com/lavinia-ped/CrossMEP_Dataset";

const THEME = {
  name: "CrossMEP",
  headFontFace: "Aptos",
  bodyFontFace: "Aptos",
  colors: {
    dk1: "0B0B0B", lt1: "FFFFFF", dk2: "1F2933", lt2: "EEF1F4",
    accent1: "2A78D6", accent2: "EB6834", accent3: "1BAF7A", accent4: "4A3AA7",
    accent5: "E34948", accent6: "008300", hlink: "2A78D6", folHlink: "4A3AA7",
  },
};
const INK2 = "52514E", MUTED = "898781", GRID = "E1E0D9", ICE = "CADCFC";
const CODE_FONT = "Aptos Mono";
const NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen"];

// Optional trace of every drawing call (DECK_TRACE=<file>).
const TRACE = process.env.DECK_TRACE ? { layouts: {}, slides: [] } : null;
const strip = (k, v) => (k === "data" && typeof v === "string" && v.length > 200 ? "<base64>" : v);
function traced(slide, layoutName) {
  if (!TRACE) return slide;
  const rec = { layout: layoutName, items: [] };
  for (const m of ["addText", "addShape", "addImage", "addChart", "addTable"]) {
    const orig = slide[m].bind(slide);
    slide[m] = (...args) => { rec.items.push({ m, args: JSON.parse(JSON.stringify(args, strip)) }); return orig(...args); };
  }
  TRACE.slides.push(rec);
  return slide;
}

// --------------------------------------------------------------------------- helpers

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

function fitImage(slide, file, box, name) {
  const { w, h } = pngSize(file);
  const ar = w / h;
  let W = box.w, H = W / ar;
  if (H > box.h) { H = box.h; W = H * ar; }
  const x = box.x + (box.w - W) / 2, y = box.y + (box.h - H) / 2;
  slide.addImage({ path: file, x, y, w: W, h: H, objectName: name || path.basename(file) });
  return { x, y, w: W, h: H };
}

// Crop src = {x, y, w, h} (source pixels) out of a PNG and fit it in box; align "center" or "top".
// Without sharp the whole image is placed instead.
async function cropImage(slide, file, box, src, name, align = "center") {
  if (!sharp) return fitImage(slide, file, box, name);
  const buf = await sharp(file).extract({ left: src.x, top: src.y, width: src.w, height: src.h }).png().toBuffer();
  const ar = src.w / src.h;
  let W = box.w, H = W / ar;
  if (H > box.h) { H = box.h; W = H * ar; }
  const x = box.x + (box.w - W) / 2, y = align === "top" ? box.y : box.y + (box.h - H) / 2;
  slide.addImage({ data: "image/png;base64," + buf.toString("base64"), x, y, w: W, h: H, objectName: name || path.basename(file) });
  return { x, y, w: W, h: H };
}

async function iconData(name, hex) {
  if (!icons || !icons[name]) return null;
  try {
    const svg = ReactDOMServer.renderToStaticMarkup(
      React.createElement(icons[name], { color: "#" + hex, size: 256, strokeWidth: 1.6 }));
    const buf = await sharp(Buffer.from(svg)).png().toBuffer();
    return "image/png;base64," + buf.toString("base64");
  } catch (e) {
    console.warn("icon " + name + " failed: " + e.message);
    return null;
  }
}

const fmtInt = (x) => Math.round(x).toLocaleString("en-US");
const fmt1 = (x) => (Math.round(x * 10) / 10).toFixed(1);

// Python-style rendering of one stored record (floats keep their ".0").
const FLOAT_KEYS = new Set(["thickness_mm", "width_mm", "height_mm", "insulation_mm", "load_kN", "span_m",
  "load_kN_per_m", "along_mm", "out_mm", "total_load_kN", "bundle_width_mm"]);
function kv(obj, keys) {
  return keys.map((k) => {
    const v = obj[k];
    const s = typeof v === "number" && FLOAT_KEYS.has(k) && Number.isInteger(v) ? v.toFixed(1) : JSON.stringify(v);
    return `"${k}": ${s}`;
  }).join(", ");
}
function recordLines(r) {
  const L = [];
  L.push(`{${kv(r, ["context_id", "tier"])},`);
  L.push(` "surface": {${kv(r.surface, ["kind", "substrate", "thickness_mm"])}},`);
  L.push(` ${kv(r, ["n_elements", "n_levels", "total_load_kN", "bundle_width_mm"])},`);
  L.push(` "elements": [`);
  r.elements.forEach((e, i) => {
    L.push(`  {${kv(e, ["kind", "service", "trade", "shape"])},`);
    L.push(`   ${kv(e, ["label", "width_mm", "height_mm", "insulation_mm"])},`);
    L.push(`   ${kv(e, ["load_kN", "span_m", "load_kN_per_m"])},`);
    L.push(`   ${kv(e, ["level", "along_mm", "out_mm"])}}${i < r.elements.length - 1 ? "," : ""}`);
  });
  L.push(` ]}`);
  return L;
}

// Extract src out of a PNG, crop it to its content (pixels that differ from the corner pixel), pad, and fit it in box.
async function trimImage(slide, file, box, src, name, align = "center", pad = 24) {
  if (!sharp) return fitImage(slide, file, box, name);
  const { data, info } = await sharp(file).extract({ left: src.x, top: src.y, width: src.w, height: src.h }).flatten({ background: "#ffffff" }).raw().toBuffer({ resolveWithObject: true });
  const ch = info.channels, bg = [data[0], data[1], data[2]];
  let x0 = info.width, y0 = info.height, x1 = -1, y1 = -1;
  for (let y = 0; y < info.height; y++) for (let x = 0; x < info.width; x++) {
    const i = (y * info.width + x) * ch;
    if (Math.abs(data[i] - bg[0]) + Math.abs(data[i + 1] - bg[1]) + Math.abs(data[i + 2] - bg[2]) > 60) {
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
  }
  x0 = Math.max(0, x0 - pad); y0 = Math.max(0, y0 - pad); x1 = Math.min(info.width - 1, x1 + pad); y1 = Math.min(info.height - 1, y1 + pad);
  const buf = await sharp(file).extract({ left: src.x + x0, top: src.y + y0, width: x1 - x0 + 1, height: y1 - y0 + 1 }).flatten({ background: "#ffffff" }).png().toBuffer();
  const ar = (x1 - x0 + 1) / (y1 - y0 + 1);
  let W = box.w, H = W / ar;
  if (H > box.h) { H = box.h; W = H * ar; }
  const x = box.x + (box.w - W) / 2, y = align === "top" ? box.y : box.y + (box.h - H) / 2;
  slide.addImage({ data: "image/png;base64," + buf.toString("base64"), x, y, w: W, h: H, objectName: name });
  return { x, y, w: W, h: H };
}

// --------------------------------------------------------------------------- deck

async function main() {
  const pres = new pptxgen();
  const C = pres.SchemeColor;
  pres.layout = "LAYOUT_WIDE";                    // 13.333 x 7.5 in
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = "Lavinia Pedrollo";
  pres.title = "CrossMEP: A Tiered Synthetic Dataset of Multi-Trade MEP Cross-Sections";
  pres.subject = "43rd International CIB W78 Conference, New Delhi, 2026";
  pres.company = "Stanford University, CIFE";

  // ---- layouts ------------------------------------------------------------
  const defineLayout = (spec) => { if (TRACE) TRACE.layouts[spec.title] = JSON.parse(JSON.stringify(spec, strip)); pres.defineSlideMaster(spec); };
  const addSlide = (opts) => traced(pres.addSlide(opts), opts.masterName);
  defineLayout({
    title: "TITLE_DARK",
    background: { color: THEME.colors.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.05, w: 7.6, h: 2.5, fontSize: 34, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "subtitle", type: "body", x: 0.7, y: 3.75, w: 7.4, h: 1.1, fontSize: 16, color: ICE, valign: "top", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "authors", type: "body", x: 0.7, y: 5.1, w: 8.4, h: 1.6, fontSize: 13, color: C.background1, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  defineLayout({
    title: "CONTENT",
    background: { color: THEME.colors.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.13, h: 1.05, fontSize: 26, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { text: { text: "CrossMEP  ·  CIB W78 2026, New Delhi", options: { x: 0.6, y: 7.02, w: 8, h: 0.3, fontSize: 9, color: MUTED, margin: 0 } } },
    ],
    slideNumber: { x: 12.1, y: 7.02, w: 0.65, h: 0.3, fontSize: 9, color: MUTED, align: "right" },
  });
  defineLayout({
    title: "CLOSING_DARK",
    background: { color: THEME.colors.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.0, w: 8.2, h: 1.9, fontSize: 36, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 4.15, w: 8.2, h: 2.2, fontSize: 16, color: ICE, valign: "top", margin: 0 }, text: "" } },
    ],
  });

  // ---- composition helpers -------------------------------------------------
  function tile(slide, x, y, w, h, big, label, opts = {}) {
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "tile " + label });
    slide.addText(big, { x: x + 0.22, y: y + 0.1, w: w - 0.44, h: h * 0.5, fontSize: opts.bigSize || 32, bold: true,
      color: opts.color || C.accent1, valign: "middle", margin: 0, isTextBox: true, objectName: "value " + label });
    slide.addText(label, { x: x + 0.22, y: y + h * 0.58, w: w - 0.44, h: h * 0.38, fontSize: opts.labelSize || 12, color: INK2,
      valign: "top", margin: 0, isTextBox: true, objectName: "label " + label });
  }

  async function iconCircle(slide, x, y, d, icon, n, name) {
    slide.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: C.accent1 }, objectName: "icon ring " + name });
    const data = icon ? await iconData(icon, THEME.colors.lt1) : null;
    if (data) {
      const s = d * 0.58;
      slide.addImage({ data, x: x + (d - s) / 2, y: y + (d - s) / 2, w: s, h: s, objectName: "icon " + name });
    } else {
      slide.addText(String(n || ""), { x, y, w: d, h: d, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    }
  }

  function bullets(slide, items, box, size = 14, name = "bullets") {
    slide.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })),
      { ...box, fontSize: size, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: name });
  }

  function caption(slide, text, box, name = "caption", size = 11) {
    slide.addText(text, { ...box, fontSize: size, color: INK2, valign: "top", margin: 0, isTextBox: true, objectName: name });
  }

  // numbered references, in order of first use; refs(slide, [n, ...]) prints the ones a slide uses in dark grey above the footer
  const REFS = {
    1: "Pedrollo, Graeber & Fischer (2026), Feasibility-aware sequential synthesis of structural support assemblies, ISARC 2026",
    2: "Pedrollo, Gvadzabia, Graeber & Fischer (2026), CrossMEP, CIB W78 2026 (this paper)",
    3: "Korman, Fischer & Tatum (2003), Knowledge and reasoning for MEP coordination, J. Constr. Eng. Manage. 129(6)",
    4: "EN 10220:2002, EN 10255:2004 (steel tubes: dimensions, medium series)",
    5: "EN 1505:1997, EN 1506:2007 (sheet-metal air ducts: rectangular and circular dimensions)",
    6: "IEC 61386-1 (conduit systems), IEC 61537 (cable tray and ladder systems)",
    7: "NEMA VE 1 (metal cable tray systems: widths, load-class spans)",
    8: "ASME B31.1 Table 121.5 (hanger spacing), as republished in the ASHRAE Handbook, HVAC Systems and Equipment",
    9: "SMACNA, HVAC Duct Construction Standards, Metal and Flexible, Table 5-1",
    10: "IET On-Site Guide (BS 7671), conduit support spacing; BS 7671 Reg. 528.3.2",
    11: "GEG (Gebäudeenergiegesetz), Anlage 8 (pipe insulation thickness)",
    12: "buildingSMART International (2020), Duplex Apartment and Medical-Dental Clinic sample IFC files, CC BY 4.0",
  };
  function refs(slide, ids, lead = "", y = 6.74, h = 0.26) {
    const text = (lead ? lead + "   " : "") + ids.map((n) => `[${n}] ${REFS[n]}`).join("   ");
    slide.addText(text, { x: 0.6, y, w: 12.13, h, fontSize: 9, color: INK2, valign: "bottom", margin: 0, isTextBox: true, objectName: "references" });
  }

  // affiliation logos on a white chip (dark slides): Stanford CEE lockup and Hilti
  async function logos(slide, x, y) {
    const W = 3.9, H = 1.3;
    slide.addShape(pres.ShapeType.roundRect, { x, y, w: W, h: H, rectRadius: 0.08, fill: { color: THEME.colors.lt1 }, objectName: "logo chip" });
    const sizes = await Promise.all(["logo_stanford_cee.png", "logo_hilti.jpg"].map((f) => sharp(path.join(FIG, f)).metadata()));
    await trimImage(slide, path.join(FIG, "logo_stanford_cee.png"), { x: x + 0.2, y: y + 0.2, w: 2.2, h: H - 0.4 }, { x: 0, y: 0, w: sizes[0].width, h: sizes[0].height }, "logo stanford", "center", 8);
    await trimImage(slide, path.join(FIG, "logo_hilti.jpg"), { x: x + 2.6, y: y + 0.42, w: 1.1, h: H - 0.84 }, { x: 0, y: 0, w: sizes[1].width, h: sizes[1].height }, "logo hilti", "center", 8);
  }

  // a thumbnail of one context: a slab (or wall) with n elements hanging from it, on a white card
  function miniCtx(s, x, y, w, h, n, kinds, color, name, wall = false) {
    const g = { fill: { color }, line: { color: THEME.colors.lt1, width: 0.4 } };
    s.addShape(pres.ShapeType.rect, { x: x - 0.05, y: y - 0.05, w: w + 0.1, h: h + 0.1, fill: { color: THEME.colors.lt1 }, line: { color: MUTED, width: 0.5 }, objectName: `mini card ${name}` });
    if (wall) {
      s.addShape(pres.ShapeType.rect, { x, y, w: 0.035, h, fill: { color: INK2 }, objectName: `mini wall ${name}` });
      const step = h / (n + 1), f = Math.min(1, step / 0.13);
      for (let i = 0; i < n; i++) {
        const cy = y + step * (i + 1), k = kinds[i % kinds.length];
        if (k === "pipe") s.addShape(pres.ShapeType.ellipse, { x: x + 0.09, y: cy - 0.045 * f, w: 0.09 * f, h: 0.09 * f, ...g, objectName: `mini ${name} ${i}` });
        else if (k === "duct") s.addShape(pres.ShapeType.rect, { x: x + 0.08, y: cy - 0.05 * f, w: 0.15 * f, h: 0.1 * f, ...g, objectName: `mini ${name} ${i}` });
        else s.addShape(pres.ShapeType.rect, { x: x + 0.08, y: cy - 0.025 * f, w: 0.12 * f, h: 0.05 * f, ...g, objectName: `mini ${name} ${i}` });
      }
      return;
    }
    s.addShape(pres.ShapeType.rect, { x, y, w, h: 0.035, fill: { color: INK2 }, objectName: `mini slab ${name}` });
    const step = w / (n + 1), f = Math.min(1, step / 0.17);
    for (let i = 0; i < n; i++) {
      const cx = x + step * (i + 1), k = kinds[i % kinds.length];
      if (k === "pipe") s.addShape(pres.ShapeType.ellipse, { x: cx - 0.045 * f, y: y + 0.08, w: 0.09 * f, h: 0.09 * f, ...g, objectName: `mini ${name} ${i}` });
      else if (k === "duct") s.addShape(pres.ShapeType.rect, { x: cx - 0.075 * f, y: y + 0.07, w: 0.15 * f, h: 0.11 * f, ...g, objectName: `mini ${name} ${i}` });
      else s.addShape(pres.ShapeType.rect, { x: cx - 0.06 * f, y: y + 0.1, w: 0.12 * f, h: 0.05 * f, ...g, objectName: `mini ${name} ${i}` });
    }
  }

  function panel(slide, x, y, w, h, name) {
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.07, fill: { color: C.background2 }, objectName: name });
  }

  function codeCard(slide, lines, box, size, name) {
    slide.addShape(pres.ShapeType.roundRect, { ...box, rectRadius: 0.07, fill: { color: C.text2 }, objectName: name + " card" });
    const runs = [];
    lines.forEach((ln, i) => {
      const hash = ln.indexOf("  #");
      const code = hash >= 0 ? ln.slice(0, hash) : ln;
      const comment = hash >= 0 ? ln.slice(hash) : "";
      const last = i === lines.length - 1;
      runs.push({ text: code || " ", options: { color: THEME.colors.lt1, breakLine: !comment && !last } });
      if (comment) runs.push({ text: comment, options: { color: ICE, breakLine: !last } });
    });
    slide.addText(runs, { x: box.x + 0.25, y: box.y + 0.2, w: box.w - 0.5, h: box.h - 0.4, fontFace: CODE_FONT,
      fontSize: size, valign: "top", margin: 0, isTextBox: true, objectName: name });
  }

  // fresh chart options every call (pptxgenjs mutates them)
  const chartStyle = (extra) => ({
    chartColors: [THEME.colors.accent1],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: THEME.colors.dk1, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: INK2, catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", catGridLine: { style: "none" },
    catAxisTitleFontFace: "+mn-lt", valAxisTitleFontFace: "+mn-lt",
    valAxisLabelColor: INK2, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: GRID, size: 0.75 },
    showLegend: false, showTitle: true, titleFontSize: 12, titleColor: THEME.colors.dk1, titleFontFace: "+mn-lt",
    ...extra,
  });

  const comp = D.composition;
  const CAT = D.catalog, CB = CAT.benchmark;
  const TR = D.trends, SEC = D.sections, LW = "length_weighted";
  const rho = (x) => (x < 0 ? "\u2212" : "+") + Math.abs(x).toFixed(2);
  const mm = (x) => String(Math.round(x));
  const span = (a, b) => `${mm(Math.min(a, b))}\u2013${mm(Math.max(a, b))}`;
  const MODEL = { clinic_plumbing: "Clinic, Plumbing", duplex_mep: "Duplex, MEP", duplex_plumbing: "Duplex, Plumbing" };
  const SHORT = { clinic_plumbing: "Clinic", duplex_mep: "Duplex MEP", duplex_plumbing: "Duplex Plumbing" };
  const w1ins = D.w1.insulation.mep, w1bare = D.w1.bare.mep, real = D.w1.real_to_real, fixed = D.w1.fixed_floor_gap;
  const gapC2 = D.tier_medians.C2.clear_gap_mm, gapC8 = D.tier_medians.C8.clear_gap_mm;
  const loadC1 = D.tier_medians.C1.load_kN, loadC8 = D.tier_medians.C8.load_kN;

  // ========================================================================= 1 title
  pres.addSection({ title: "Opening" });
  {
    const s = addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
    s.addText([{ text: "CrossMEP: A Tiered Synthetic", options: { breakLine: true } },
      { text: "Dataset of Multi-Trade MEP", options: { breakLine: true } },
      { text: "Cross-Sections" }], { placeholder: "title" });
    s.addText("A support-design problem distribution for learning-based structural support assembly synthesis", { placeholder: "subtitle" });
    s.addText([
      { text: "Lavinia Pedrollo ¹  ·  David Gvadzabia ²  ·  Torben Graeber ³  ·  Martin Fischer ¹", options: { bold: true, breakLine: true } },
      { text: "¹ Stanford University, CIFE   ² Lafayette College   ³ Hilti AG", options: { breakLine: true, color: ICE } },
      { text: " ", options: { breakLine: true, fontSize: 6 } },
      { text: "43rd International CIB W78 Conference · IT in Construction · New Delhi, 6–8 October 2026", options: { color: ICE } },
    ], { placeholder: "authors" });
    s.addImage({ path: path.join(FIG, "title_art.png"), x: 8.5, y: 1.6, w: 4.4, h: 2.75, objectName: "title art" });
    s.addText("a generated C8 context: eight services on three rows", { x: 8.5, y: 4.45, w: 4.4, h: 0.3, fontSize: 10, color: ICE, align: "right", margin: 0, isTextBox: true, objectName: "art caption" });
    await logos(s, 9.0, 5.35);
    s.addNotes("Hi, I'm Lavinia, a PhD student at Stanford University, and today I am happy to present CrossMEP, which is the dataset we built when we found that the data to learn support design from did not exist. Support design is the one part of MEP that every tool coordinates, every tool checks, and no tool does. A hospital has ten thousand of these supports, each chosen by hand from a catalog. We think a machine can learn to choose them, and what has stopped anyone trying is not the algorithm. It is that nobody had the problems to practise on. So we built the problems. (0:00)");
  }

  // ========================================================================= 2 the assemblies (from the ISARC 2026 talk)
  pres.addSection({ title: "Motivation" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText([{ text: "The synthesis of structural support assemblies (SSAs) takes 25% of MEP design effort because every assembly must be designed individually", options: { fontSize: 22, bold: true } }], { placeholder: "title" });
    const b = { x: 0.6, y: 1.45, w: 6.6, h: 6.6 * 720 / 1280 };
    s.addImage({ path: path.join(FIG, "isarc_building.jpg"), ...b, objectName: "hospital model" });
    const z = { x: b.x + 0.4567 * b.w, y: b.y + 0.4318 * b.h, w: 0.0982 * b.w, h: 0.1396 * b.h };
    const ins = { x: 7.6, y: 1.95, w: 5.13, h: 5.13 * 728 / 1268 };
    const RED = "C00000";
    const orange = { color: RED, width: 1.5 };
    s.addShape(pres.ShapeType.rect, { ...z, fill: { type: "none" }, line: orange, objectName: "zoom box" });
    s.addShape(pres.ShapeType.line, { x: z.x + z.w, y: Math.min(z.y, ins.y), w: ins.x - z.x - z.w, h: Math.abs(ins.y - z.y), line: orange, flipV: ins.y < z.y, objectName: "zoom line top" });
    s.addShape(pres.ShapeType.line, { x: z.x + z.w, y: z.y + z.h, w: ins.x - z.x - z.w, h: ins.y + ins.h - z.y - z.h, line: orange, objectName: "zoom line bottom" });
    s.addImage({ path: path.join(FIG, "isarc_ssa.jpg"), ...ins, objectName: "one assembly" });
    s.addShape(pres.ShapeType.rect, { ...ins, fill: { type: "none" }, line: orange, objectName: "inset frame" });
    s.addText("1 unit = 1 structural support assembly (SSA)", { x: ins.x, y: 1.45, w: ins.w, h: 0.45, fontSize: 15, bold: true, color: C.text1, valign: "bottom", margin: 0, isTextBox: true, objectName: "inset label" });
    const tw = (12.13 - 2 * 0.2) / 3;
    const stat = async (x, icon, big, lead, label, name) => {
      panel(s, x, 5.35, tw, 1.3, "tile " + name);
      s.addShape(pres.ShapeType.ellipse, { x: x + 0.25, y: 5.35 + 0.33, w: 0.64, h: 0.64, fill: { color: RED }, objectName: "icon ring " + name });
      const d = await iconData(icon, THEME.colors.lt1);
      if (d) s.addImage({ data: d, x: x + 0.25 + 0.64 * 0.21, y: 5.35 + 0.33 + 0.64 * 0.21, w: 0.64 * 0.58, h: 0.64 * 0.58, objectName: "icon " + name });
      s.addText(big, { x: x + 1.1, y: 5.42, w: tw - 1.3, h: 0.6, fontSize: 28, bold: true, color: RED, valign: "middle", margin: 0, isTextBox: true, objectName: "value " + name });
      s.addText([{ text: lead + " ", options: { bold: true, color: RED } }, { text: label, options: { color: INK2 } }],
        { x: x + 1.1, y: 6.02, w: tw - 1.3, h: 0.58, fontSize: 12, valign: "top", margin: 0, isTextBox: true, objectName: "label " + name });
    };
    await stat(0.6, "FiLayers", "≈ 10,000", "support assemblies", "in one 200,000 sq ft hospital project", "assemblies");
    await stat(0.6 + tw + 0.2, "FiClock", "20 min – 2 h", "of engineering time", "for each assembly, designed one by one", "time");
    await stat(0.6 + 2 * (tw + 0.2), "FiDollarSign", "≈ $600k", "of engineering cost", "cumulative per hospital project", "effort");
    refs(s, [1], "Approximate practitioner estimates [1].");
    s.addNotes("Here is the scale. This is a hospital, and every red mark is a place where services hang from the structure. A modular support groups several services on one prefabricated frame: a structural support assembly. A hospital this size needs about ten thousand of them, each designed individually, twenty minutes to two hours apiece. Add it up and it is about a quarter of the MEP design effort. Practitioner estimates, but these are the numbers people live with. (0:45)");
  }

  // ========================================================================= 3 the problem: one cross-section in, verified support designs out (from the ISARC 2026 talk)
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("An SSA designer turns one MEP cross-section into a feasible structural support assembly", { placeholder: "title" });
    const PY = 2.0, PH = 3.0, PW = 5.3, LX = 0.6, RX = 7.43;
    const head = (x, t, name) => s.addText(t, { x, y: 1.45, w: PW, h: 0.3, fontSize: 16, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "head " + name });
    const frame = (x, y, name, line = { color: GRID, width: 1 }) =>
      s.addShape(pres.ShapeType.roundRect, { x, y, w: PW, h: PH, rectRadius: 0.06, fill: { color: THEME.colors.lt1 }, line, objectName: "frame " + name });
    const ceiling = (x, name) => {
      const cx = x + 0.2, cy = PY + 0.2, cw = PW - 0.4, ch = 0.42;
      s.addShape(pres.ShapeType.rect, { x: cx, y: cy, w: cw, h: ch, fill: { color: THEME.colors.lt2 }, line: { color: INK2, width: 0.75 }, objectName: "ceiling " + name });
      for (let hx = cx; hx + 0.3 <= cx + cw + 1e-6; hx += 0.3)
        s.addShape(pres.ShapeType.line, { x: hx, y: cy, w: 0.3, h: ch, flipV: true, line: { color: MUTED, width: 0.5 }, objectName: `hatch ${name} ${hx.toFixed(1)}` });
      s.addText("Concrete ceiling", { x: cx + cw / 2 - 0.85, y: cy + 0.07, w: 1.7, h: ch - 0.14, fontSize: 11, color: C.text1, fill: { color: THEME.colors.lt1 },
        align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "ceiling label " + name });
      return { x: cx, y: cy, w: cw, h: ch };
    };
    // the same services in both panels; on the right they sit on the trapeze (dy)
    const services = (x, name, dy = 0) => {
      const g = { fill: { color: THEME.colors.lt2 }, line: { color: INK2, width: 1 } };
      const yb = PY + 2.25 + dy;
      s.addShape(pres.ShapeType.rect, { x: x + 0.45, y: yb - 0.95, w: 1.55, h: 0.95, ...g, objectName: "duct " + name });
      s.addText("Duct", { x: x + 0.45, y: yb - 0.95, w: 1.55, h: 0.95, fontSize: 12, color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "duct label " + name });
      s.addShape(pres.ShapeType.ellipse, { x: x + 2.35, y: yb - 0.7, w: 0.7, h: 0.7, ...g, objectName: "pipe a " + name });
      s.addShape(pres.ShapeType.ellipse, { x: x + 3.2, y: yb - 0.45, w: 0.45, h: 0.45, ...g, objectName: "pipe b " + name });
      s.addShape(pres.ShapeType.rect, { x: x + 3.7, y: yb - 0.3, w: 1.0, h: 0.3, ...g, objectName: "tray " + name });
      return yb;
    };

    // in: the context
    frame(LX, PY, "in");
    ceiling(LX, "in");
    const ybL = services(LX, "in");
    s.addText("Pipes", { x: LX + 2.35, y: ybL + 0.08, w: 1.3, h: 0.3, fontSize: 12, color: C.text1, align: "center", margin: 0, isTextBox: true, objectName: "pipes label" });
    s.addText("Cable tray", { x: LX + 3.6, y: ybL + 0.08, w: 1.2, h: 0.3, fontSize: 12, color: C.text1, align: "center", margin: 0, isTextBox: true, objectName: "tray label" });

    // design
    s.addShape(pres.ShapeType.line, { x: LX + PW + 0.2, y: PY + PH / 2, w: RX - LX - PW - 0.4, h: 0, line: { color: INK2, width: 1.5, endArrowType: "triangle" }, objectName: "design arrow" });
    s.addText("design", { x: LX + PW, y: PY + PH / 2 - 0.4, w: RX - LX - PW, h: 0.3, fontSize: 11.5, color: INK2, align: "center", margin: 0, isTextBox: true, objectName: "design label" });

    // out: the assemblies, a stack of verified designs
    frame(RX, PY, "out", { color: INK2, width: 0.75 });
    const cl = ceiling(RX, "out");
    const ybR = services(RX, "out", -0.15);
    const bar = { x: RX + 0.3, y: ybR, w: PW - 0.6, h: 0.09 };
    [bar.x + 0.08, bar.x + bar.w - 0.2].forEach((rx, i) => {
      s.addShape(pres.ShapeType.rect, { x: rx - 0.02, y: cl.y + cl.h - 0.12, w: 0.16, h: 0.16, fill: { color: THEME.colors.dk2 }, objectName: "anchor " + i });
      s.addShape(pres.ShapeType.rect, { x: rx + 0.04, y: cl.y + cl.h, w: 0.04, h: bar.y - cl.y - cl.h, fill: { color: THEME.colors.dk2 }, objectName: "rod " + i });
    });
    s.addShape(pres.ShapeType.rect, { ...bar, fill: { color: THEME.colors.dk2 }, objectName: "trapeze bar" });
    s.addText("Rod trapeze", { x: RX + 0.25, y: PY + PH - 0.5, w: 2.5, h: 0.35, fontSize: 13, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "assembly name" });
    s.addText("✓ verified", { x: RX + PW - 2.0, y: PY + PH - 0.5, w: 1.75, h: 0.35, fontSize: 13, bold: true, color: THEME.colors.accent6, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: "verified" });

    // the two words the talk relies on
    s.addNotes("So what exactly is designed, and from what? In: one cross-section at a hanger. The structure it hangs from, and the services crossing it, each with its trade, position, size and weight per metre. We call that the context. It is the brief. Out: assemblies of catalog parts that carry those services to the structure, checked for statics, anchors, connectors and buildability, ranked by cost. That is the answer. Hold on to these two words, because CrossMEP is contexts only. It contains no assemblies. (1:15)");
  }

  // ========================================================================= 4 the synthesis problem (from the ISARC 2026 talk)
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText([{ text: "Existing tools coordinate and verify modular support assemblies, but their synthesis remains manual because it relies on tacit engineering expertise and complex catalog-driven rules", options: { fontSize: 22, bold: true } }], { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "paper_fig1_route_to_section.png"), { x: 0.6, y: 1.5, w: 7.4, h: 2.75 }, "route to section");
    caption(s, "Design starts after coordination [3]: at each hanger the designer works from the section across the run, not from the whole model [2].",
      { x: img.x, y: img.y + img.h + 0.1, w: img.w, h: 0.5 }, "fig1 caption");
    panel(s, 8.25, 1.5, 4.48, 2.85, "practice card");
    await iconCircle(s, 8.5, 1.68, 0.5, "FiTool", "", "practice");
    s.addText([
      { text: "Where practice stands", options: { bold: true, fontSize: 17, breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Tools coordinate the model and check a design.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Choosing the topology and the parts, from a fixed catalog, is still done by hand, one section at a time [1].", options: {} },
    ], { x: 9.15, y: 1.65, w: 3.4, h: 2.6, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "practice" });
    const why = [
      ["Geometric judgment", "Engineers choose an assembly’s topology from experience.", "FiEye"],
      ["Rule explosion", "Code, load and material constraints interact across thousands of combinations.", "FiGitBranch"],
      ["Catalog volatility", "Catalogs change faster than rule-based systems can be rewritten.", "FiRefreshCw"],
    ];
    const cw = (12.13 - 2 * 0.2) / 3;
    for (const [i, [h, t, icon]] of why.entries()) {
      const x = 0.6 + i * (cw + 0.2);
      panel(s, x, 4.65, cw, 1.6, "why " + h);
      await iconCircle(s, x + 0.25, 4.8, 0.5, icon, "", "why " + h);
      s.addText(`${i + 1}. ${h}`, { x: x + 0.9, y: 4.8, w: cw - 1.1, h: 0.5, fontSize: 17, bold: true, color: C.accent1, valign: "middle", margin: 0, isTextBox: true, objectName: "why head " + h });
      s.addText(t, { x: x + 0.25, y: 5.4, w: cw - 0.5, h: 0.8, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "why text " + h });
    }
    refs(s, [1, 2, 3]);
    s.addNotes("Why is this still done by hand? A designer works from one section at each hanger, after coordination. Tools coordinate the model and check a design, but they do not choose the layout or the parts. Three reasons it has resisted automation: the topology comes from experience, the rules interact across thousands of combinations, and catalogs change faster than rule systems can be rewritten. (1:50)");
  }

  // ========================================================================= 5 why contexts: a learning loop needs many of them (the approach stays a black box)
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("A learning method needs thousands of contexts to practise on, and real projects give too few, so we generate them", { placeholder: "title" });
    const NY = 1.95, NH = 1.5;
    const g = { fill: { color: THEME.colors.lt1 }, line: { color: INK2, width: 0.75 } };
    const text = (box, head, body, headColor, bodyColor, name, headSize = 14, bodySize = 11) =>
      s.addText([{ text: head, options: { bold: true, fontSize: headSize, color: headColor, breakLine: true } },
                 { text: body, options: { fontSize: bodySize, color: bodyColor } }],
        { ...box, valign: "top", align: "center", margin: 0.06, isTextBox: true, objectName: "text " + name });
    const arrow = (x0, x1, y, name) =>
      s.addShape(pres.ShapeType.line, { x: x0, y, w: x1 - x0, h: 0, line: { color: INK2, width: 1.5, endArrowType: "triangle" }, objectName: "arrow " + name });
    const label = (x, y, w, t, name, color = INK2, size = 10.5) =>
      s.addText(t, { x, y, w, h: 0.26, fontSize: size, color, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "label " + name });
    const pic = async (icon, hex, x, w, name) => { const d = await iconData(icon, hex); if (d) s.addImage({ data: d, x: x + (w - 0.5) / 2, y: NY + 0.14, w: 0.5, h: 0.5, objectName: "icon " + name }); };

    // the loop: context -> method -> design -> check, and pass or fail back into the method
    const CX = 0.6, CW = 2.3, MX = 3.55, MW = 2.7, DX = 6.9, DW = 2.3, KX = 9.85, KW = 2.88;
    s.addText("How a learning method learns, round after round", { x: 0.6, y: 1.45, w: 5.0, h: 0.3, fontSize: 12, bold: true, color: INK2, margin: 0, isTextBox: true, objectName: "loop heading" });
    // context
    s.addShape(pres.ShapeType.roundRect, { x: CX, y: NY, w: CW, h: NH, rectRadius: 0.06, fill: { color: C.background2 }, line: { color: C.accent1, width: 1.5 }, objectName: "box context" });
    miniCtx(s, CX + 0.55, NY + 0.17, CW - 1.1, 0.42, 4, ["duct", "pipe", "pipe", "tray"], C.accent1, "loop context");
    text({ x: CX, y: NY + 0.68, w: CW, h: NH - 0.7 }, "Context", "one section at a hanger, without the answer", C.text1, INK2, "context");
    // method: a black box
    s.addShape(pres.ShapeType.roundRect, { x: MX, y: NY, w: MW, h: NH, rectRadius: 0.06, fill: { color: THEME.colors.dk1 }, objectName: "black box method" });
    await pic("FiCpu", THEME.colors.lt1, MX, MW, "method");
    text({ x: MX, y: NY + 0.68, w: MW, h: NH - 0.7 }, "Learning method", "a black box that proposes a design", THEME.colors.lt1, ICE, "method");
    arrow(CX + CW, MX, NY + NH / 2, "context to method");
    // proposed design: a small rod trapeze
    s.addShape(pres.ShapeType.roundRect, { x: DX, y: NY, w: DW, h: NH, rectRadius: 0.06, fill: { color: C.background2 }, line: { color: INK2, width: 1 }, objectName: "box design" });
    const TX = DX + 0.65, TW = DW - 1.3;
    s.addShape(pres.ShapeType.rect, { x: TX, y: NY + 0.14, w: TW, h: 0.08, fill: { color: THEME.colors.lt2 }, line: { color: INK2, width: 0.5 }, objectName: "mini out slab" });
    [TX + 0.08, TX + TW - 0.11].forEach((rx, i) => s.addShape(pres.ShapeType.rect, { x: rx, y: NY + 0.22, w: 0.03, h: 0.38, fill: { color: THEME.colors.dk2 }, objectName: "mini rod " + i }));
    s.addShape(pres.ShapeType.rect, { x: TX, y: NY + 0.58, w: TW, h: 0.04, fill: { color: THEME.colors.dk2 }, objectName: "mini bar" });
    s.addShape(pres.ShapeType.ellipse, { x: TX + 0.25, y: NY + 0.38, w: 0.2, h: 0.2, ...g, objectName: "mini out pipe a" });
    s.addShape(pres.ShapeType.ellipse, { x: TX + 0.55, y: NY + 0.43, w: 0.15, h: 0.15, ...g, objectName: "mini out pipe b" });
    text({ x: DX, y: NY + 0.68, w: DW, h: NH - 0.7 }, "Proposed design", "an assembly: channel, rods, clamps, anchors", C.text1, INK2, "design");
    arrow(MX + MW, DX, NY + NH / 2, "method to design");
    // check
    s.addShape(pres.ShapeType.roundRect, { x: KX, y: NY, w: KW, h: NH, rectRadius: 0.06, fill: { color: "EAF5EE" }, line: { color: THEME.colors.accent6, width: 1.5 }, objectName: "box check" });
    await pic("FiCheckCircle", THEME.colors.accent6, KX, KW, "check");
    text({ x: KX, y: NY + 0.68, w: KW, h: NH - 0.7 }, "Check", "statics, anchors, connectors, buildability, cost", C.text1, INK2, "check");
    arrow(DX + DW, KX, NY + NH / 2, "design to check");
    // feedback, over the top
    const FY = 1.75, mxc = MX + MW / 2, kxc = KX + KW / 2;
    s.addShape(pres.ShapeType.line, { x: kxc, y: FY, w: 0, h: NY - FY, line: { color: THEME.colors.accent6, width: 1.5, dashType: "dash" }, objectName: "feedback up" });
    s.addShape(pres.ShapeType.line, { x: mxc, y: FY, w: kxc - mxc, h: 0, line: { color: THEME.colors.accent6, width: 1.5, dashType: "dash" }, objectName: "feedback across" });
    s.addShape(pres.ShapeType.line, { x: mxc, y: FY, w: 0, h: NY - FY, line: { color: THEME.colors.accent6, width: 1.5, dashType: "dash", endArrowType: "triangle" }, objectName: "feedback down" });
    label(mxc + 0.3, FY - 0.3, kxc - mxc - 0.6, "pass or fail is fed back, and the method improves", "feedback", THEME.colors.accent6, 11);

    // the two sources sit in one frame, called out from the context box with dotted lines
    const BY = 4.45, BH = 2.1, BW2 = 5.83, GX = 6.83;
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 4.38, w: 12.21, h: 2.24, rectRadius: 0.07, fill: { color: C.background2 }, line: { color: C.accent1, width: 1.5 }, objectName: "sources frame" });
    s.addShape(pres.ShapeType.line, { x: CX, y: NY + NH, w: 0, h: 4.38 - NY - NH, line: { color: C.accent1, width: 1.5, dashType: "sysDot" }, objectName: "callout left" });
    s.addShape(pres.ShapeType.line, { x: CX + CW, y: NY + NH, w: 12.81 - CX - CW, h: 4.38 - NY - NH, line: { color: C.accent1, width: 1.5, dashType: "sysDot" }, objectName: "callout right" });

    // where the contexts come from
    const card = (x, head, tag, tagColor, body, name, tagW = 1.6) => {
      s.addShape(pres.ShapeType.roundRect, { x, y: BY, w: BW2, h: BH, rectRadius: 0.07, fill: { color: THEME.colors.lt1 }, line: { color: tagColor, width: 1.5 }, objectName: "card " + name });
      s.addText(head, { x: x + 0.25, y: BY + 0.12, w: 3.2, h: 0.36, fontSize: 15, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "card head " + name });
      s.addShape(pres.ShapeType.roundRect, { x: x + BW2 - tagW - 0.25, y: BY + 0.15, w: tagW, h: 0.3, rectRadius: 0.15, fill: { color: tagColor }, objectName: "card tag " + name });
      s.addText(tag, { x: x + BW2 - tagW - 0.25, y: BY + 0.15, w: tagW, h: 0.3, fontSize: 10.5, bold: true, color: THEME.colors.lt1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "card tag text " + name });
      s.addText(body, { x: x + 0.25, y: BY + 1.3, w: BW2 - 0.5, h: BH - 1.4, fontSize: 11.5, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "card body " + name });
    };
    card(0.67, "Real projects", "too few, not diverse enough", THEME.colors.accent2,
      "A handful of sections, from one project with one trade mix, and confidential. Not enough to practise on, and a method tuned on them only fits that project.", "real", 2.3);
    // six near-identical thumbnails, with empty slots after them
    for (let i = 0; i < 6; i++) miniCtx(s, 0.67 + 0.3 + i * 0.62, BY + 0.62, 0.5, 0.42, 3, ["pipe"], THEME.colors.accent2, "real " + i);
    for (let i = 6; i < 9; i++) s.addShape(pres.ShapeType.rect, { x: 0.67 + 0.25 + i * 0.62, y: BY + 0.57, w: 0.6, h: 0.52, fill: { type: "none" }, line: { color: MUTED, width: 0.5, dashType: "dash" }, objectName: "empty slot " + i });
    card(GX, "CrossMEP generates them", "unlimited, diverse", C.accent1,
      "As many contexts as a method needs: every tier from one to eight elements, kinds and surfaces varied, a new seed a new set. And one fixed benchmark, never trained on, to judge every method on.", "generated");
    const rows = [["pipe"], ["duct", "pipe", "tray", "pipe"], ["pipe", "tray", "pipe"]];
    for (let n = 1; n <= 8; n++) miniCtx(s, GX + 0.3 + (n - 1) * 0.68, BY + 0.62, 0.56, 0.42, n, rows[n % 3], C.accent1, "gen " + n, n % 4 === 3);
    s.addNotes("So how would a machine learn it? Give it a context. Let it propose an assembly. Check the assembly, and feed pass or fail back. Round after round, it gets better. But every round needs a new context, and that is where it stops. Real projects give a handful of sections, all from the same kind of job and confidential: too few to practise on, and a method tuned on them only fits that job. So we generate the contexts, as many as a method needs, and we fix one benchmark to judge every method on. (2:15)");
  }

  // ========================================================================= 6 gap + at a glance
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("The ninety real designs we had came from one project and filled one corner of the design space, so CrossMEP covers all of it by construction", { placeholder: "title" });
    // the design space: element count across, kinds / surface up. Real designs: a few near-identical
    // sections in one corner. CrossMEP: a section for every tier, with kinds and surfaces varied.
    const plot = (x, y, w, h, head, sub, name) => {
      panel(s, x, y, w, h, "space " + name);
      s.addText([{ text: head, options: { bold: true, fontSize: 14, color: C.text1 } }, { text: "   " + sub, options: { fontSize: 11.5, color: INK2 } }],
        { x: x + 0.2, y: y + 0.1, w: w - 0.4, h: 0.32, valign: "middle", margin: 0, isTextBox: true, objectName: "space head " + name });
      const ax = { x: x + 0.5, y: y + 0.52, w: w - 0.75, h: h - 0.95 };
      s.addShape(pres.ShapeType.line, { x: ax.x, y: ax.y + ax.h, w: ax.w, h: 0, line: { color: INK2, width: 1, endArrowType: "triangle" }, objectName: "x axis " + name });
      s.addShape(pres.ShapeType.line, { x: ax.x, y: ax.y, w: 0, h: ax.h, line: { color: INK2, width: 1, beginArrowType: "triangle" }, objectName: "y axis " + name });
      s.addText("elements at the hanger: 1 … 8", { x: ax.x, y: ax.y + ax.h + 0.03, w: ax.w, h: 0.25, fontSize: 10, color: INK2, align: "center", margin: 0, isTextBox: true, objectName: "x label " + name });
      s.addText("kinds, trades, surface", { x: x - 0.03, y: ax.y, w: 0.5, h: ax.h, fontSize: 10, color: INK2, align: "center", valign: "middle", rotate: 270, margin: 0, isTextBox: true, objectName: "y label " + name });
      return ax;
    };
    const mini = (...a) => miniCtx(s, ...a);
    const left = plot(0.6, 1.5, 5.7, 2.3, "The real designs we had", "ninety · one project · confidential", "real");
    // ninety near-identical sections in one corner: a duct with many pipes, never a tray, never a single pipe
    [[0.5, 0.62], [0.64, 0.62], [0.78, 0.62], [0.54, 0.3], [0.68, 0.3], [0.82, 0.3]].forEach(([u, v], i) =>
      mini(left.x + u * left.w, left.y + (1 - v) * left.h - 0.26, 0.6, 0.26, 6 + (i % 3), ["duct", "pipe", "pipe", "pipe"], THEME.colors.accent2, "real " + i));
    s.addShape(pres.ShapeType.ellipse, { x: left.x + 0.44 * left.w, y: left.y + 0.1 * left.h, w: 0.54 * left.w, h: 0.78 * left.h, fill: { type: "none" }, line: { color: THEME.colors.accent2, width: 1, dashType: "dash" }, objectName: "real cluster ring" });
    s.addText([{ text: "ducts and many pipes, no trays, nothing as simple as one pipe", options: { breakLine: true } }, { text: "a method tuned here only fits that project", options: { italic: true } }],
      { x: left.x + 0.02, y: left.y + 0.12 * left.h, w: 0.4 * left.w, h: 0.75 * left.h, fontSize: 11, color: INK2, valign: "middle", margin: 0, isTextBox: true, objectName: "real note" });
    const right = plot(0.6, 3.95, 5.7, 2.3, "CrossMEP", "every tier · kinds and surfaces varied · unlimited", "synthetic");
    // one column per tier (n elements), three rows: pipes; mixed kinds; on a wall
    const rows = [["pipe"], ["duct", "pipe", "tray", "pipe"], ["pipe", "tray", "pipe"]];
    const cw2 = right.w / 8, rh = right.h / 3;
    for (let n = 1; n <= 8; n++) rows.forEach((kinds, r) => {
      const x = right.x + (n - 1) * cw2 + 0.09, y = right.y + r * rh + 0.08;
      mini(x, y, cw2 - 0.18, rh - 0.16, n, kinds, C.accent1, `syn ${n}${r}`, r === 2);
    });
    s.addText("CrossMEP at a glance", { x: 6.35, y: 1.5, w: 6.38, h: 0.4, fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "glance heading" });
    const tw = (6.38 - 0.2) / 2, th = 1.3;
    const tiles = [
      [fmtInt(comp.contexts), "contexts in four splits, on disjoint seeds", "FiDatabase"],
      [fmtInt(comp.elements), "elements: pipes, trays, ducts, conduits; six trades", "FiGrid"],
      ["C1–C8", "eight tiers by exact element count", "FiBarChart2"],
      ["0 labels", "the brief, not the answer", "FiTag"],
      ["Traced", "every constant sourced or declared", "FiBookOpen"],
      ["Open", "data CC BY 4.0, code MIT, seeded generator", "FiUnlock"],
    ];
    for (const [i, [big, label, icon]] of tiles.entries()) {
      const r = Math.floor(i / 2), c = i % 2, x = 6.35 + c * (tw + 0.2), y = 2.0 + r * (th + 0.17);
      panel(s, x, y, tw, th, "glance " + big);
      await iconCircle(s, x + 0.22, y + 0.33, 0.64, icon, "", "glance " + big);
      s.addText(big, { x: x + 1.05, y: y + 0.12, w: tw - 1.2, h: 0.55, fontSize: 24, bold: true, color: C.accent1, valign: "middle", margin: 0, isTextBox: true, objectName: "glance value " + big });
      s.addText(label, { x: x + 1.05, y: y + 0.68, w: tw - 1.2, h: 0.55, fontSize: 11.5, color: INK2, valign: "top", margin: 0, isTextBox: true, objectName: "glance label " + big });
    }
    s.addNotes("How scarce? The real designs we could get were ninety, from one project. Nearly every one had a duct and many pipes. Not one had a cable tray, and not one was as simple as a single pipe: one corner of the design space. A method tuned on them measures fit to that project. So CrossMEP fills the space by construction: every tier from one element to eight, kinds and surfaces varied, without limit. A new seed is a new set. Seven thousand contexts are the release, not the ceiling. (2:55)");
  }

  // studio captures (scripts/screenshot_contexts.js): crop boxes and the trade colours of the 3D view
  const TRADE = { domestic: ["domestic water", THEME.colors.accent1], heating: ["heating", THEME.colors.accent2], chilled: ["chilled water", THEME.colors.accent3],
                  sprinkler: ["sprinkler", THEME.colors.accent5], electrical: ["electrical", THEME.colors.accent4], ventilation: ["ventilation", THEME.colors.accent6] };
  const SHEET = { x: 60, y: 60, w: 2520, h: 1480 };      // the drawing area of the A4 sheet, inside the frame and above the title block
  const VIEW3D = { x: 20, y: 20, w: 2600, h: 860 };      // the 3D view above its key

  // ========================================================================= 7 anatomy
  pres.addSection({ title: "The dataset" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("One context is exactly what a support designer receives at one hanger, without the answer", { placeholder: "title" });
    // the studio section captured by scripts/screenshot_contexts.js (tier C5, seed 8, section 11), with its stored record
    const ctx = JSON.parse(fs.readFileSync(path.join(FIG, "11_c5.json"), "utf8")).record;
    let gap = Infinity;   // closest clear gap between insulation surfaces, as crossmep.tasks.min_clear_gap (ceiling)
    ctx.elements.forEach((p, i) => ctx.elements.slice(i + 1).forEach((q) => {
      const da = Math.abs(p.along_mm - q.along_mm) - (p.width_mm + q.width_mm) / 2 - p.insulation_mm - q.insulation_mm;
      const dn = Math.abs(p.out_mm - q.out_mm) - (p.height_mm + q.height_mm) / 2 - p.insulation_mm - q.insulation_mm;
      gap = Math.min(gap, Math.max(da, dn));
    }));

    // left: the section as a support detail, then the same run in 3D beside what every element carries
    const sheet = await trimImage(s, path.join(FIG, "11_c5_sheet.png"), { x: 0.6, y: 1.45, w: 6.3, h: 3.05 }, SHEET, "section sheet", "top");
    s.addShape(pres.ShapeType.rect, { x: sheet.x - 0.06, y: sheet.y - 0.06, w: sheet.w + 0.12, h: sheet.h + 0.12, fill: { type: "none" }, line: { color: GRID, width: 0.75 }, objectName: "sheet frame" });
    const v3 = await trimImage(s, path.join(FIG, "11_c5_3d.png"), { x: 0.6, y: 4.7, w: 2.7, h: 1.95 }, VIEW3D, "section 3d", "top");
    const legend = [...new Set(ctx.elements.map((e) => e.trade))].flatMap((t) => [{ text: "● ", options: { color: TRADE[t][1] } }, { text: TRADE[t][0] + "   ", options: { color: INK2 } }]);
    s.addText(legend, { x: 0.6, y: 6.68, w: 3.2, h: 0.22, fontSize: 9, margin: 0, isTextBox: true, objectName: "3d legend" });
    s.addText("What every element carries", { x: 3.55, y: 4.7, w: 3.35, h: 0.3, fontSize: 12, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "fields heading" });
    const chips = ["kind", "service, trade", "size", "insulation", "position", "load = kN/m × span"];
    let cx = 3.55, cy = 5.1;
    chips.forEach((t) => {
      const w = 0.24 + t.length * 0.064;
      if (cx + w > 6.9) { cx = 3.55; cy += 0.46; }
      s.addShape(pres.ShapeType.roundRect, { x: cx, y: cy, w, h: 0.34, rectRadius: 0.17, fill: { color: THEME.colors.lt2 }, line: { color: GRID, width: 0.75 }, objectName: "chip " + t });
      s.addText(t, { x: cx, y: cy, w, h: 0.34, fontSize: 10, color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "chip text " + t });
      cx += w + 0.12;
    });

    // right: the record as the designer reads it
    const RX = 7.15, RW = 12.73 - RX;
    s.addText("What the support designer is given", { x: RX, y: 1.45, w: RW, h: 0.35, fontSize: 14, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "given heading" });
    const hdr = (t, a) => ({ text: t, options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.dk2 }, fontSize: 11, align: a || "left" } });
    const cell = (t, a, b) => ({ text: t, options: { fontSize: 11, color: THEME.colors.dk1, align: a || "left", bold: !!b } });
    const rows = [[hdr("Element"), hdr("Trade"), hdr("Ins. mm", "right"), hdr("kN/m", "right"), hdr("Span", "right"), hdr("kN at support", "right")]];
    ctx.elements.forEach((e) => {
      const [name, color] = TRADE[e.trade];
      rows.push([cell(e.label.replace("x", "×"), "left", true),
        { text: [{ text: "● ", options: { color, fontSize: 11 } }, { text: name, options: { color: THEME.colors.dk1, fontSize: 11 } }], options: { align: "left" } },
        cell(String(Math.round(e.insulation_mm)), "right"), cell(e.load_kN_per_m.toFixed(3), "right"), cell(`${e.span_m.toFixed(1)} m`, "right"), cell(e.load_kN.toFixed(2), "right", true)]);
    });
    s.addTable(rows, { x: RX, y: 1.85, w: RW, colW: [1.35, 1.3, 0.7, 0.7, 0.65, RW - 4.7], fontFace: THEME.bodyFontFace, fontSize: 11,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.34, valign: "middle", margin: 0.06, objectName: "record table" });

    // three facts about the whole context
    const facts = [
      ["FiLayers", `${Math.round(ctx.surface.thickness_mm)} mm`, `${ctx.surface.kind} slab, ${ctx.surface.substrate.replace("_", " ")}`],
      ["FiArrowDown", `${ctx.total_load_kN.toFixed(2)} kN`, "total load at this support"],
      ["FiMinimize2", `${Math.round(gap)} mm`, `closest clear gap, ${ctx.n_levels} rows`],
    ];
    const fw = (RW - 0.3) / 3, FY = 1.85 + 0.34 * rows.length + 0.25;
    for (const [i, [icon, big, label]] of facts.entries()) {
      const x = RX + i * (fw + 0.15);
      panel(s, x, FY, fw, 1.0, "fact " + label);
      await iconCircle(s, x + 0.15, FY + 0.25, 0.5, icon, "", "fact " + label);
      s.addText([{ text: big, options: { bold: true, fontSize: 12.5, color: C.text1, breakLine: true } }, { text: label, options: { fontSize: 9.5, color: INK2 } }],
        { x: x + 0.75, y: FY + 0.08, w: fw - 0.85, h: 0.84, valign: "middle", margin: 0, isTextBox: true, objectName: "fact text " + label });
    }

    // what is deliberately absent
    const NY = FY + 1.2;
    s.addShape(pres.ShapeType.roundRect, { x: RX, y: NY, w: RW, h: 6.64 - NY, rectRadius: 0.07, fill: { color: THEME.colors.dk2 }, objectName: "absent band" });
    const slash = await iconData("FiSlash", THEME.colors.lt1);
    if (slash) s.addImage({ data: slash, x: RX + 0.25, y: NY + (6.64 - NY) / 2 - 0.25, w: 0.5, h: 0.5, objectName: "icon absent" });
    s.addText([{ text: "Not given, by design: ", options: { bold: true, color: THEME.colors.lt1 } },
               { text: "channel, rods, clamps, anchors. No correct answer either: a feasible support depends on the catalog you build from.", options: { color: ICE } }],
      { x: RX + 0.95, y: NY, w: RW - 1.15, h: 6.64 - NY, fontSize: 12, valign: "middle", margin: 0, isTextBox: true, objectName: "absent text" });
    s.addNotes("Here is one context: a two-dimensional section at one support. Each element has its kind, service and trade, its size, insulation and position, and its load: weight per metre times the span it was sized at. Add the surface, slab or wall, and that is all. No channel, no rods, no anchors, no correct answer, because a feasible support depends on the catalog you build from. (3:35)");
  }

  // ========================================================================= 8 generation
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("Every section is built the way trades run services, with gaps measured on a real building", { placeholder: "title" });
    const steps = [
      ["FiHash", "Tier", "Cn fixes the exact element count, n = 1 … 8"],
      ["FiLayers", "Surface", "ceiling or wall (78 / 22 %); concrete, 150–300 mm thick"],
      ["FiGitMerge", "Services", "grouped as trades run [3]: hot + cold, flow + return, conduit groups, 1–2 trays, ducts"],
      ["FiAlignCenter", "Rows", "bulky first: ducts nearest the slab, then trays and conduits, then pipes"],
      ["FiMove", "Spacing", "gaps drawn from a built project [12], at least 25 mm; electrical above wet on walls [10]"],
      ["FiCheckCircle", "Check", "every pair 25 mm clear, rows centred, everything recorded; same seed, same file"],
    ];
    const SY = 1.55, SH = 0.72, SG = 0.14;
    s.addShape(pres.ShapeType.line, { x: 0.82, y: SY + 0.22, w: 0, h: (SH + SG) * 5, line: { color: GRID, width: 2 }, objectName: "step spine" });
    for (const [i, [icon, head, text]] of steps.entries()) {
      const y = SY + i * (SH + SG);
      panel(s, 1.2, y, 5.5, SH, "step card " + (i + 1));
      s.addShape(pres.ShapeType.ellipse, { x: 0.6, y: y + SH / 2 - 0.22, w: 0.44, h: 0.44, fill: { color: C.accent1 }, line: { color: THEME.colors.lt1, width: 1.5 }, objectName: "step circle " + (i + 1) });
      s.addText(String(i + 1), { x: 0.6, y: y + SH / 2 - 0.22, w: 0.44, h: 0.44, fontSize: 13, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "step number " + (i + 1) });
      const data = await iconData(icon, THEME.colors.dk2);
      if (data) s.addImage({ data, x: 1.38, y: y + SH / 2 - 0.17, w: 0.34, h: 0.34, objectName: "step icon " + head });
      s.addText([{ text: head, options: { bold: true, color: C.text1, breakLine: true } }, { text, options: { color: INK2, fontSize: 11.5 } }],
        { x: 1.9, y, w: 4.65, h: SH, fontSize: 13, valign: "middle", margin: 0, isTextBox: true, objectName: "step " + (i + 1) });
    }
    const ctx8 = JSON.parse(fs.readFileSync(path.join(FIG, "12_c8.json"), "utf8")).record;
    const sheet8 = await trimImage(s, path.join(FIG, "12_c8_sheet.png"), { x: 6.95, y: 1.5, w: 5.78, h: 2.95 }, SHEET, "generated sheet", "top");
    s.addShape(pres.ShapeType.rect, { x: sheet8.x - 0.06, y: sheet8.y - 0.06, w: sheet8.w + 0.12, h: sheet8.h + 0.12, fill: { type: "none" }, line: { color: GRID, width: 0.75 }, objectName: "generated sheet frame" });
    const v38 = await trimImage(s, path.join(FIG, "12_c8_3d.png"), { x: 6.95, y: 4.6, w: 2.75, h: 1.85 }, VIEW3D, "generated 3d", "top");
    const legend8 = [...new Set(ctx8.elements.map((e) => e.trade))].flatMap((t) => [{ text: "● ", options: { color: TRADE[t][1] } }, { text: TRADE[t][0] + "   ", options: { color: INK2 } }]);
    s.addText(legend8, { x: 6.95, y: 6.48, w: 3.0, h: 0.22, fontSize: 9, margin: 0, isTextBox: true, objectName: "generated 3d legend" });
    caption(s, `One generated context, tier ${ctx8.tier}: ${ctx8.n_elements} services on ${ctx8.n_levels} rows, ducts nearest the slab, then the tray and conduits, then the pipe. The gap marked on the sheet is one draw from the measured distribution; the same seed gives the same section.`,
      { x: 9.95, y: 4.6, w: 2.78, h: 1.9 }, "generation caption", 11);
    refs(s, [3, 10, 12]);
    s.addNotes("How is a context made? By rules an engineer would recognize. The tier fixes the element count. We pick the surface and fill it the way trades run services: hot and cold together, flow and return together, conduits in groups, bulky services nearest the slab. Gaps are drawn from gaps measured on a built project, never below twenty-five millimetres. On walls, electrical stays above water. Same seed, same file. (4:00)");
  }

  // ========================================================================= 9 sources
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("Every number is traced to a standard, to a measurement, or to a choice we declare as ours", { placeholder: "title" });
    // left: the five element kinds, each with its size standard and load basis; a glyph per kind
    const glyph = (kind, x, y) => {
      const g = { fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.dk2, width: 1 } };
      if (kind === "pipe") s.addShape(pres.ShapeType.ellipse, { x: x + 0.1, y: y + 0.1, w: 0.36, h: 0.36, ...g, objectName: "glyph pipe" });
      if (kind === "insulation") {
        s.addShape(pres.ShapeType.ellipse, { x: x + 0.04, y: y + 0.04, w: 0.48, h: 0.48, fill: { type: "none" }, line: { color: THEME.colors.dk2, width: 1, dashType: "dash" }, objectName: "glyph insulation ring" });
        s.addShape(pres.ShapeType.ellipse, { x: x + 0.16, y: y + 0.16, w: 0.24, h: 0.24, ...g, objectName: "glyph insulation pipe" });
      }
      if (kind === "tray") { s.addShape(pres.ShapeType.rect, { x: x + 0.04, y: y + 0.3, w: 0.48, h: 0.05, fill: { color: THEME.colors.dk2 }, objectName: "glyph tray base" });
        [x + 0.04, x + 0.47].forEach((rx, i) => s.addShape(pres.ShapeType.rect, { x: rx, y: y + 0.18, w: 0.05, h: 0.17, fill: { color: THEME.colors.dk2 }, objectName: "glyph tray side " + i })); }
      if (kind === "duct") s.addShape(pres.ShapeType.rect, { x: x + 0.04, y: y + 0.12, w: 0.48, h: 0.32, ...g, objectName: "glyph duct" });
      if (kind === "conduit") [0, 1, 2].forEach((i) => s.addShape(pres.ShapeType.ellipse, { x: x + 0.05 + i * 0.17, y: y + 0.2, w: 0.14, h: 0.14, ...g, objectName: "glyph conduit " + i }));
    };
    const kinds = [
      ["pipe", "Pipes DN15–150", "EN 10220 / EN 10255 medium series [4]", "steel + water × ASME B31.1 water-service span [8]"],
      ["insulation", "Insulation", "GEG Anlage 8, heated lines [11]; 30 / 50 mm condensation control, chilled", "adds to the size, not the load"],
      ["tray", "Cable trays 150–600", "IEC 61537 systems [6] in NEMA VE 1 widths [7]", "50 kg/m full at 300 mm × 2.0 m, below the shortest NEMA class span [7]"],
      ["duct", "Ducts", "EN 1505 rectangular, EN 1506 round [5]", "manufacturer weight table with flanges × 2.4 m (SMACNA) [9]"],
      ["conduit", "Conduits Ø20–50", "IEC 61386-1 [6], parallel groups of 2–6", "steel tube + 40 % cable fill × 2.0 m (IET / BS 7671) [10]"],
    ];
    const KY = 1.5, KH = 0.78, KW = 7.45;
    for (const [i, [kind, name, sizes, load]] of kinds.entries()) {
      const y = KY + i * (KH + 0.1);
      panel(s, 0.6, y, KW, KH, "kind " + name);
      s.addShape(pres.ShapeType.roundRect, { x: 0.72, y: y + 0.11, w: 0.56, h: 0.56, rectRadius: 0.06, fill: { color: THEME.colors.lt1 }, line: { color: GRID, width: 0.75 }, objectName: "glyph card " + name });
      glyph(kind, 0.72, y + 0.11);
      s.addText(name, { x: 1.45, y: y + 0.05, w: 1.75, h: KH - 0.1, fontSize: 13, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "kind name " + name });
      s.addText([{ text: "Sizes  ", options: { bold: true, color: C.accent1 } }, { text: sizes, options: { color: C.text1, breakLine: true } },
                 { text: "Load  ", options: { bold: true, color: C.accent1 } }, { text: load, options: { color: C.text1 } }],
        { x: 3.25, y: y + 0.05, w: KW - 2.85, h: KH - 0.1, fontSize: 10.5, valign: "middle", margin: 0, isTextBox: true, objectName: "kind text " + name });
    }

    // right: the three kinds of ground, colour coded
    const GX = 8.3, GW = 12.73 - GX, GH = (KH * 5 + 0.4 - 0.3) / 3;
    const grounds = [
      ["FiBookOpen", C.accent1, "Standards", "what each element is and weighs: sizes, walls, spans, insulation [4]–[11]"],
      ["FiCrosshair", THEME.colors.accent3, "Measured", "how close neighbours sit: clear gaps and row stagger from two open buildings [12]"],
      ["FiEdit3", THEME.colors.accent2, "Declared", "our choices, labelled as such: trade mix, ceiling / wall 78 / 22 %, number of rows"],
    ];
    for (const [i, [icon, color, head, body]] of grounds.entries()) {
      const y = KY + i * (GH + 0.15);
      panel(s, GX, y, GW, GH, "ground " + head);
      s.addShape(pres.ShapeType.roundRect, { x: GX + 0.08, y: y + 0.14, w: 0.08, h: GH - 0.28, rectRadius: 0.04, fill: { color }, objectName: "ground bar " + head });
      s.addShape(pres.ShapeType.ellipse, { x: GX + 0.3, y: y + GH / 2 - 0.29, w: 0.58, h: 0.58, fill: { color }, objectName: "ground ring " + head });
      const data = await iconData(icon, THEME.colors.lt1);
      if (data) s.addImage({ data, x: GX + 0.3 + 0.13, y: y + GH / 2 - 0.16, w: 0.32, h: 0.32, objectName: "ground icon " + head });
      s.addText([{ text: head, options: { bold: true, fontSize: 14, color: C.text1, breakLine: true } }, { text: body, options: { fontSize: 11, color: INK2 } }],
        { x: GX + 1.05, y, w: GW - 1.25, h: GH, valign: "middle", margin: 0, isTextBox: true, objectName: "ground text " + head });
    }
    caption(s, "Every constant carries its source and its status, and why each standard was chosen over its alternatives is written down with it.", { x: 0.6, y: 5.88, w: 12.13, h: 0.3 }, "sources note", 11);
    refs(s, [4, 5, 6, 7, 8, 9, 10, 11, 12], "", 6.22, 0.76);
    s.addNotes("Where do the numbers come from? Sizes, weights and spans from standards: EN for pipes and ducts, IEC for conduits and trays, ASME for spans, GEG for insulation. Spacing from measured open buildings. And a few choices of our own, like the trade mix, labelled as choices. (4:30)");
  }

  // ========================================================================= 10 tiers and the design check (gallery + experiment 1)
  pres.addSection({ title: "Experiments" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText("The tier fixes the element count, and load and congestion grow with it as the rules intend", { placeholder: "title" });
    // the design check: medians per tier, benchmark (125 per tier) and population (2,000 per tier)
    const tiers = D.tiers, lb = TR.benchmark.load_kN.per_tier, lp = TR.population.load_kN.per_tier;
    const gb = TR.benchmark.clear_gap_mm.per_tier, gp = TR.population.clear_gap_mm.per_tier, gt = tiers.slice(1);
    const two = (extra) => chartStyle({ chartColors: [THEME.colors.accent1, "B9C0BB"], showLegend: true, legendPos: "b", legendFontSize: 9, legendFontFace: "+mn-lt",
      barGrouping: "clustered", barGapWidthPct: 60, dataLabelFontSize: 10, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, titleFontSize: 14, legendFontSize: 10, ...extra });
    s.addChart(pres.ChartType.bar, [
      { name: "benchmark median", labels: tiers, values: tiers.map((t) => lb[t].median) },
      { name: `population median (${fmtInt(TR.settings.per_tier)} per tier)`, labels: tiers, values: tiers.map((t) => lp[t].median) }],
      two({ x: 0.6, y: 1.45, w: 5.95, h: 4.75, barDir: "col", dataLabelFormatCode: "0.00", valAxisLabelFormatCode: "0.0", valAxisMinVal: 0,
        title: "Heavier with the tier: median load at the support (kN)", objectName: "load chart" }));
    s.addChart(pres.ChartType.bar, [
      { name: "benchmark median", labels: gt, values: gt.map((t) => gb[t].median) },
      { name: `population median (${fmtInt(TR.settings.per_tier)} per tier)`, labels: gt, values: gt.map((t) => gp[t].median) }],
      two({ x: 6.78, y: 1.45, w: 5.95, h: 4.75, barDir: "col", dataLabelFormatCode: "0", valAxisLabelFormatCode: "0", valAxisMinVal: 0,
        title: "Tighter with the tier: median closest clear gap (mm)", objectName: "gap chart" }));
    caption(s, `A check that the dataset behaves as designed, not a discovery: the tier fixes the element count; load and congestion follow from the rules. Within a tier, kinds, trades, surfaces and stacking all vary. Load rises with the tier (rank correlation ${rho(TR.benchmark.load_kN.spearman)} on the benchmark, 125 contexts per tier; the population medians rise at every step) and the closest gap narrows at every step (${rho(TR.benchmark.clear_gap_mm.spearman)}); intervals are bootstrapped over contexts.`,
      { x: 0.6, y: 6.3, w: 12.13, h: 0.55 }, "experiment 1 caption", 11);
    s.addNotes("Three analyses. The first is a design check. Each tier adds one element: C1 is a single service, the most common support in any building; C8 has eight. Within a tier everything else varies, so the element count is the one controlled axis. Load at the support rises with the tier, from about 0.3 to 2.0 kilonewtons, and the closest gap narrows at every step, from 130 to about 51 millimetres. The dataset behaves as designed. (4:50)");
  }

  // ========================================================================= 11 experiment 2
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText(`Generated spacing matches a clinic the generator never saw to within ${mm(SEC.gen_to_real.clinic_plumbing[LW].w1)} millimetres`, { placeholder: "title" });
    const g = SEC.gen_to_real, r = SEC.real_to_real;
    const gc = g.clinic_plumbing[LW];
    // left: the two gap distributions, share of pipe pairs per 25 mm bin
    const H = D.gap_hist;
    s.addChart(pres.ChartType.bar, [
      { name: `measured: Medical-Dental Clinic, ${fmtInt(H.clinic_pairs)} pipe pairs`, labels: H.bin_mm.map(String), values: H.clinic.map((v) => 100 * v) },
      { name: `generated: CrossMEP benchmark, ${fmtInt(H.generated_pairs)} pipe pairs`, labels: H.bin_mm.map(String), values: H.generated.map((v) => 100 * v) }],
      chartStyle({ x: 0.6, y: 1.45, w: 5.9, h: 4.1, barDir: "col", barGrouping: "clustered", barGapWidthPct: 30, chartColors: [THEME.colors.accent1, THEME.colors.accent2],
        showValue: false, showLegend: true, legendPos: "t", legendFontSize: 9, legendFontFace: "+mn-lt", catAxisLabelFontSize: 8, catAxisLabelFrequency: 4,
        valAxisLabelFormatCode: "0", valAxisTitle: "share of pipe pairs (%)", showValAxisTitle: true, valAxisTitleFontSize: 9,
        catAxisTitle: "clear gap between neighbouring pipes, bare surfaces (mm)", showCatAxisTitle: true, catAxisTitleFontSize: 9,
        title: "A building the generator never saw", objectName: "gap histogram" }));
    // right: Wasserstein-1 distances with 95 % intervals, drawn to scale
    const rows = [["generated ↔ Clinic", gc, THEME.colors.accent2], ["Duplex MEP ↔ Duplex Plumbing", r["duplex_mep|duplex_plumbing"][LW], THEME.colors.accent1],
                  ["generated ↔ Duplex MEP", g.duplex_mep[LW], THEME.colors.accent2], ["Clinic ↔ Duplex MEP", r["clinic_plumbing|duplex_mep"][LW], THEME.colors.accent1],
                  ["generated ↔ Duplex Plumbing", g.duplex_plumbing[LW], THEME.colors.accent2], ["Clinic ↔ Duplex Plumbing", r["clinic_plumbing|duplex_plumbing"][LW], THEME.colors.accent1]];
    const PX = 6.75, PW = 5.98, PY = 1.45, PH = 4.1;
    panel(s, PX, PY, PW, PH, "distance panel");
    s.addText("How far apart the distributions are: Wasserstein-1 (mm) with 95 % interval", { x: PX + 0.2, y: PY + 0.08, w: PW - 0.4, h: 0.3, fontSize: 12, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "distance title" });
    const AX = PX + 2.55, AW = PW - 2.95, AY = PY + 0.55, AH = PH - 1.05, XMAX = 160;
    const xpos = (v) => AX + Math.min(v, XMAX) / XMAX * AW;
    [0, 40, 80, 120, 160].forEach((v) => {
      s.addShape(pres.ShapeType.line, { x: xpos(v), y: AY, w: 0, h: AH, line: { color: GRID, width: 0.75 }, objectName: "grid " + v });
      s.addText(String(v), { x: xpos(v) - 0.3, y: AY + AH + 0.02, w: 0.6, h: 0.22, fontSize: 9, color: INK2, align: "center", margin: 0, isTextBox: true, objectName: "tick " + v });
    });
    const rh = AH / rows.length;
    rows.forEach(([label, v, color], i) => {
      const y = AY + rh * (i + 0.5);
      s.addText(label, { x: PX + 0.15, y: y - 0.15, w: 2.35, h: 0.3, fontSize: 9.5, color: C.text1, align: "right", valign: "middle", margin: 0, isTextBox: true, objectName: "row " + label });
      s.addShape(pres.ShapeType.line, { x: xpos(v.lo), y, w: xpos(v.hi) - xpos(v.lo), h: 0, line: { color, width: 2.5 }, objectName: "ci " + label });
      s.addShape(pres.ShapeType.ellipse, { x: xpos(v.w1) - 0.07, y: y - 0.07, w: 0.14, h: 0.14, fill: { color }, line: { color: THEME.colors.lt1, width: 0.75 }, objectName: "w1 " + label });
      if (v.noise_floor) s.addShape(pres.ShapeType.line, { x: xpos(v.noise_floor.median), y: y - 0.1, w: 0, h: 0.2, line: { color: MUTED, width: 1.5 }, objectName: "floor " + label });
      s.addText(mm(v.w1), { x: xpos(v.hi) + 0.05, y: y - 0.13, w: 0.5, h: 0.26, fontSize: 10, bold: i === 0, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "value " + label });
    });
    s.addText([{ text: "● ", options: { color: THEME.colors.accent2 } }, { text: "generated vs a real model     ", options: { color: INK2 } },
               { text: "● ", options: { color: THEME.colors.accent1 } }, { text: "real vs real     ", options: { color: INK2 } },
               { text: "|  noise floor: what a perfect generator would show", options: { color: INK2 } }],
      { x: PX + 0.2, y: PY + PH - 0.3, w: PW - 0.4, h: 0.25, fontSize: 9, margin: 0, isTextBox: true, objectName: "distance legend" });
    const tw = (12.13 - 2 * 0.2) / 3;
    tile(s, 0.6, 5.72, tw, 0.95, `${mm(gc.w1)} mm`, `generator to clinic (95 % CI ${mm(gc.lo)}–${mm(gc.hi)}); fitted on the duplex, clinic held out`, { bigSize: 20, labelSize: 10 });
    tile(s, 0.6 + tw + 0.2, 5.72, tw, 0.95, `${mm(r["duplex_mep|duplex_plumbing"][LW].w1)} mm`, "the duplex's own two models from each other: about as close as real is to real", { bigSize: 20, labelSize: 10 });
    tile(s, 0.6 + 2 * (tw + 0.2), 5.72, tw, 0.95, `${Math.round(gc.fixed_25mm / 10) * 10} mm`, "what a fixed 25 mm gap would be from the clinic", { bigSize: 20, labelSize: 10 });
    refs(s, [12], `Sections every 250 mm, clinic pipe pairs weighted by shared length; models: buildingSMART Duplex Apartment and Medical-Dental Clinic [12].`, 6.74);
    s.addNotes(`The second is the one the generator could fail: is the spacing realistic in a building it has never seen? The gap distribution was fitted on a residential duplex. We held out a medical clinic, cut it into sections every 250 millimetres, and measured the gaps between pipes side by side. Generator to clinic: ${mm(gc.w1)} millimetres. Above the ${mm(gc.noise_floor.median)} a perfect generator would show, but about as close as the duplex's own two models are to each other. A fixed 25-millimetre gap would be about ${Math.round(gc.fixed_25mm / 10) * 10} off. (5:20)`);
  }

  // ========================================================================= 12 experiment 3
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText(`The paper’s two clamp sizes reach one pipe in ${NUMBER_WORDS[Math.round(100 / CB.pct_pipes)]}, and the dataset says which sizes to add`, { placeholder: "title" });
    const sizes = Object.keys(CAT.by_size);
    s.addChart(pres.ChartType.bar, [
      { name: "attachable", labels: sizes, values: sizes.map((k) => CAT.by_size[k].covered) },
      { name: "no size fits", labels: sizes, values: sizes.map((k) => CAT.by_size[k].pipes - CAT.by_size[k].covered) }],
      chartStyle({ x: 0.6, y: 1.45, w: 6.0, h: 3.55, barDir: "col", barGrouping: "stacked", barGapWidthPct: 45,
        chartColors: [THEME.colors.accent1, "CFCDC3"], dataLabelPosition: "ctr", dataLabelFormatCode: "#,##0;;;",
        dataLabelFontSize: 11, layout: { x: 0.08, y: 0.14, w: 0.9, h: 0.62 }, dataLabelColor: THEME.colors.dk1, valAxisLabelFormatCode: "#,##0", valAxisMinVal: 0,
        valAxisMaxVal: 600, valAxisMajorUnit: 100, showLegend: true, legendPos: "b", legendFontSize: 10, legendColor: INK2,
        title: "Pipes by nominal size: what the two-size catalog attaches", objectName: "attach by size chart" }));
    const curve = CAT.demand.curve;
    s.addChart(pres.ChartType.bar, [{ name: "best possible share (%)", labels: curve.map((r) => String(r.k)), values: curve.map((r) => r.pct) }],
      chartStyle({ x: 6.75, y: 1.45, w: 5.98, h: 3.55, barDir: "col", barGapWidthPct: 45, dataLabelFormatCode: "0",
        dataLabelFontSize: 11, layout: { x: 0.08, y: 0.14, w: 0.9, h: 0.62 }, valAxisLabelFormatCode: "0", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 20,
        showCatAxisTitle: true, catAxisTitle: `number of clamp sizes, each fitting a ${CAT.demand.width_mm} mm diameter window`,
        catAxisTitleFontSize: 10, catAxisTitleColor: INK2,
        title: "Best share of pipes (%) that any k clamp sizes could attach", objectName: "demand chart" }));
    const tw = (12.13 - 2 * 0.2) / 3;
    const k2 = curve.find((r) => r.k === 2).pct, k6 = curve.find((r) => r.k === 6).pct;
    tile(s, 0.6, 5.1, tw, 1.6, `${fmt1(CB.pct_pipes)} %`,
      `of benchmark pipes attachable with the paper’s two sizes [2] (95 % CI ${fmt1(CB.ci[0])}–${fmt1(CB.ci[1])}); every one is DN40`, { labelSize: 11 });
    tile(s, 0.6 + tw + 0.2, 5.1, tw, 1.6, `${fmt1(k2)} %`,
      `with two sizes placed where the pipes are; ${Math.round(k6)} % with six, and every pipe with ${curve.length}`, { labelSize: 11 });
    tile(s, 0.6 + 2 * (tw + 0.2), 5.1, tw, 1.6, `0 of ${fmtInt(CB.not_pipe)}`,
      `trays, ducts and conduits: a pipe-clamp catalog defines no attachment. Load never binds (${CB.max_pipe_load_kN.toFixed(2)} vs ${CB.min_bin_capacity_kN.toFixed(1)} kN)`, { labelSize: 11 });
    refs(s, [2]);
    s.addNotes(`The third is a use of the dataset: what must a catalog of clamps cover? Our paper's two-size catalog attaches ${fmt1(CB.pct_pipes)} percent of the pipes, interval ${Math.round(CB.ci[0])} to ${Math.round(CB.ci[1])}, all one size, DN40. Trays, ducts and conduits are not covered at all. On the right, what the dataset asks of any catalog: two well-placed sizes reach ${Math.round(k2)} percent, six sizes ${Math.round(k6)}, ${NUMBER_WORDS[curve.length] || curve.length} every pipe. What the catalog should contain becomes a measurement. (5:55)`);
  }

  // ========================================================================= 13 demo
  pres.addSection({ title: "Use" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Use" });
    s.addText("Pick a tier or an exact mix and a seed, and the Generator Studio returns the designer’s brief", { placeholder: "title" });
    const demo = path.join(FIG, "08_studio_demo.png");
    const frame = (box, name) => s.addShape(pres.ShapeType.rect, { x: box.x - 0.05, y: box.y - 0.05, w: box.w + 0.1, h: box.h + 0.1, fill: { type: "none" }, line: { color: GRID, width: 0.75 }, objectName: name });
    // in: the parameters bar
    s.addText("In: the parameters", { x: 0.6, y: 1.4, w: 6, h: 0.25, fontSize: 10, bold: true, color: INK2, margin: 0, isTextBox: true, objectName: "in label" });
    const bar = await cropImage(s, demo, { x: 0.6, y: 1.7, w: 12.13, h: 0.75 }, { x: 30, y: 16, w: 2660, h: 176 }, "studio parameters", "top");
    frame(bar, "parameters frame");
    // out: the drawing sheet with the facts line, and the same run in 3D
    const dwg = await trimImage(s, demo, { x: 0.6, y: 2.95, w: 7.55, h: 2.75 }, { x: 180, y: 560, w: 1300, h: 530 }, "studio section", "top", 14);
    frame(dwg, "section frame");
    const facts = await cropImage(s, demo, { x: 0.6, y: dwg.y + dwg.h + 0.17, w: 7.55, h: 0.36 }, { x: 30, y: 1455, w: 1400, h: 72 }, "studio facts", "top");
    s.addText("Out: section A–A as the designer receives it, and what it carries", { x: 0.6, y: 2.65, w: 7.55, h: 0.25, fontSize: 10, bold: true, color: INK2, margin: 0, isTextBox: true, objectName: "out label" });
    const x = 8.45, w = 12.73 - x;
    const v3 = await trimImage(s, demo, { x, y: 2.95, w, h: 2.3 }, { x: 1720, y: 330, w: 950, h: 1000 }, "studio 3D", "top", 10);
    frame(v3, "3d frame");
    s.addText("Out: the same run in 3D, cut at the section", { x, y: 2.65, w, h: 0.25, fontSize: 10, bold: true, color: INK2, margin: 0, isTextBox: true, objectName: "out 3d label" });
    panel(s, x, 5.4, w, 1.25, "studio link card");
    s.addImage({ path: path.join(FIG, "qr_studio.png"), x: x + 0.12, y: 5.46, w: 1.13, h: 1.13, objectName: "qr studio" });
    s.addText([{ text: "Scan to open the studio", options: { bold: true, color: C.text1, breakLine: true } },
               { text: "every section is a stored output of the released generator, with the call that reproduces it", options: { color: INK2, fontSize: 10.5 } }],
      { x: x + 1.35, y: 5.4, w: w - 1.5, h: 1.25, fontSize: 12.5, valign: "middle", margin: 0, isTextBox: true, objectName: "studio link" });
    s.addNotes("Let me show it. This is the Generator Studio. I choose what crosses the hanger, a tier or an exact mix, and a seed. Out comes the section a designer receives, drawn as an engineer would issue it: every service at true size, its level, its load, the closest gap, and the run in 3D. Every section is a stored output of the released generator. Scan the code to try it. [Live: switch to the studio, click C3, then Generate another twice, then Exact mix with a duct. If the demo fails, stay on this slide: its screenshot is the fallback. Before the talk: open the studio once with internet, set its link sharing to public, scan the QR from a phone not logged in.] (6:25)");
  }
  // ========================================================================= 14 using it
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Use" });
    s.addText("Methods train on the generator and are compared on one fixed benchmark, tier by tier", { placeholder: "title" });
    // the protocol as a flow: generator -> train -> benchmark -> report
    const steps = [
      ["FiCpu", "Generator", "unlimited problems: a new seed is a new set; a curriculum from C1 up to C8"],
      ["FiLayers", "Train", `${fmtInt(D.splits.train.contexts)} contexts (seed ${D.splits.train.seed}); validation ${fmtInt(D.splits.val.contexts)}, test ${fmtInt(D.splits.test.contexts)}, on their own seeds`],
      ["FiTarget", "Benchmark", `${fmtInt(D.splits.benchmark.contexts)} contexts, 125 per tier, seed ${D.splits.benchmark.seed}: never trained on, the same for every method`],
      ["FiBarChart2", "Report", "per tier, with 95 % intervals and paired tests between methods"],
    ];
    const FW = 2.5, FG = (12.13 - 4 * FW) / 3, FY = 1.5, FH = 2.25;
    const links = ["train on", "evaluate on", "then"];
    for (const [i, [icon, head, body]] of steps.entries()) {
      const x = 0.6 + i * (FW + FG);
      panel(s, x, FY, FW, FH, "flow " + head);
      await iconCircle(s, x + 0.25, FY + 0.25, 0.6, icon, "", "flow " + head);
      s.addText(head, { x: x + 1.0, y: FY + 0.25, w: FW - 1.2, h: 0.6, fontSize: 16, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "flow head " + head });
      s.addText(body, { x: x + 0.25, y: FY + 1.0, w: FW - 0.5, h: FH - 1.15, fontSize: 12, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "flow text " + head });
      if (i < 3) {
        s.addShape(pres.ShapeType.line, { x: x + FW + 0.05, y: FY + 0.55, w: FG - 0.1, h: 0, line: { color: INK2, width: 1.5, endArrowType: "triangle" }, objectName: "flow arrow " + i });
        s.addText(links[i], { x: x + FW - 0.25, y: FY + 0.6, w: FG + 0.5, h: 0.25, fontSize: 9.5, color: INK2, align: "center", margin: 0, isTextBox: true, objectName: "flow link " + i });
      }
    }
    codeCard(s, [
      "import crossmep.tasks as cm",
      "data = cm.load(\"benchmark\")  # 1,000 contexts, or generate your own mix",
      "from crossmep.evaluate import score, compare",
      "score(my_results, data)  # per tier, 95 % CI    compare(mine, baseline, data)  # paired test",
    ], { x: 0.6, y: 4.1, w: 12.13, h: 1.45 }, 13, "code");
    caption(s, "Four lines to load, score and compare; loading, metrics and scoring need only the Python standard library, the generator needs NumPy. The same files serve reinforcement learning, constraint programming and benchmarking: there are no labels to fit a method to.",
      { x: 0.6, y: 5.7, w: 12.13, h: 0.55 }, "code caption", 11.5);
    s.addNotes("Using it takes a few lines: load a split, filter by composition, or generate your own mix. Four splits on disjoint seeds: five thousand to train, five hundred each for validation and test, and a benchmark of a thousand, a hundred and twenty-five per tier. The same files serve reinforcement learning, constraint programming and benchmarking, and we ship the scoring. Train on the generator. Evaluate on the benchmark, the same contexts for every method. Report per tier, with intervals and paired tests. (7:30)");
  }

  // ========================================================================= 15 scope & next
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Use" });
    s.addText("Today CrossMEP is one section at one support, and next come a checker and real projects", { placeholder: "title" });
    const cw = (12.13 - 0.25) / 2, x2 = 0.6 + cw + 0.25;
    const column = async (x, head, rows, numbered, name) => {
      panel(s, x, 1.5, cw, 3.55, name + " card");
      s.addText(head, { x: x + 0.3, y: 1.6, w: cw - 0.6, h: 0.4, fontSize: 18, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: name + " heading" });
      const rh = (3.55 - 0.65) / rows.length;
      for (const [i, [icon, text]] of rows.entries()) {
        const y = 2.1 + i * rh;
        await iconCircle(s, x + 0.3, y + rh / 2 - 0.22, 0.44, numbered ? null : icon, i + 1, name + " " + i);
        s.addText(text, { x: x + 0.95, y, w: cw - 1.2, h: rh, fontSize: 12.5, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: name + " text " + i });
      }
    };
    await column(0.6, "Scope", [
      ["FiCrop", "One cross-section at one support: routing, branches and support spacing are outside it; the span is recorded, so a method can vary it"],
      ["FiCheckCircle", "Realism checked on two open buildings, a residential duplex and a medical clinic; congested racks rest on practice and standards"],
      ["FiEdit3", "Trade mix and tier composition are design choices, not survey results"],
      ["FiAlertTriangle", "Synthetic: not for the structural design of real installations"],
    ], false, "scope");
    await column(x2, "Next", [
      [null, "A public checker for support designs, with best-known costs from an exact solver on the small tiers"],
      [null, "The catalog as an input: generated catalogs, and catalogs a method has never seen"],
      [null, "A real test set: sections from commercial projects with supports designed by engineers"],
    ], true, "next");
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.3, w: 12.13, h: 1.35, rectRadius: 0.07, fill: { color: C.text2 }, objectName: "ask band" });
    s.addText([{ text: "If you coordinate services or design supports, ", options: { bold: true } },
      { text: "open the studio, generate the sections you know from your projects, and tell us what looks wrong. Every rule is one documented constant away from being changed." }],
      { x: 0.95, y: 5.4, w: 10.0, h: 1.15, fontSize: 15, color: C.background1, valign: "middle", margin: 0, isTextBox: true, objectName: "ask" });
    s.addImage({ path: path.join(FIG, "qr_repo.png"), x: 11.55, y: 5.42, w: 1.1, h: 1.1, objectName: "qr ask" });
    s.addNotes("Scope. CrossMEP is one section at one support. Pipe spacing was checked on two open buildings; the rest rests on practice and standards, and the trade mix is a design choice. It is not for the structural design of real installations. Next: a public checker, so methods can be compared on the answer; the catalog as an input; and a real test set from commercial projects, with supports designed by engineers. That is where I would value your eye. (8:05)");
  }

  // ========================================================================= 16 closing
  {
    const s = addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Use" });
    s.addText("Support design finally has open problems to learn from", { placeholder: "title" });
    s.addText([
      { text: "CrossMEP is the brief, not the answer: seven thousand support-design problems, open to anyone who wants to teach a machine to design supports.", options: { breakLine: true } },
      { text: " ", options: { breakLine: true, fontSize: 6 } },
      { text: "Data CC BY 4.0, code MIT.  Not for the structural design of real installations.", options: { fontSize: 12, color: ICE } },
    ], { placeholder: "body" });
    // four takeaways as icon tiles on the dark ground
    const takeaways = [["FiDatabase", fmtInt(comp.contexts), "support-design problems in eight tiers"], ["FiBookOpen", "Sourced", "every constant sourced or declared"],
                       ["FiCheckCircle", "Checked", "pipe gaps tested on two open buildings"], ["FiUnlock", "Open", "data, code and generator"]];
    const tw = (8.2 - 3 * 0.15) / 4;
    for (const [i, [icon, big, label]] of takeaways.entries()) {
      const x = 0.7 + i * (tw + 0.15), y = 5.25;
      s.addShape(pres.ShapeType.roundRect, { x, y, w: tw, h: 1.45, rectRadius: 0.07, fill: { color: "2B3946" }, objectName: "takeaway " + big });
      const data = await iconData(icon, ICE);
      if (data) s.addImage({ data, x: x + 0.18, y: y + 0.18, w: 0.34, h: 0.34, objectName: "takeaway icon " + big });
      s.addText(big, { x: x + 0.62, y: y + 0.12, w: tw - 0.75, h: 0.45, fontSize: 17, bold: true, color: THEME.colors.lt1, valign: "middle", margin: 0, isTextBox: true, objectName: "takeaway value " + big });
      s.addText(label, { x: x + 0.18, y: y + 0.65, w: tw - 0.36, h: 0.72, fontSize: 10.5, color: ICE, valign: "top", margin: 0, isTextBox: true, objectName: "takeaway label " + big });
    }
    s.addImage({ path: path.join(FIG, "qr_repo.png"), x: 9.85, y: 1.75, w: 2.2, h: 2.2, objectName: "qr closing" });
    s.addText([{ text: REPO, options: { bold: true, breakLine: true } }, { text: "laviniap@stanford.edu" }],
      { x: 9.0, y: 4.05, w: 3.9, h: 0.75, fontSize: 12, color: C.background1, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: "closing link" });
    await logos(s, 9.0, 5.35);
    s.addNotes("To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design problems, every constant sourced or declared, spacing checked on two open buildings, all of it open. If you coordinate services or design supports, try the studio and tell me what looks wrong. Thank you. (8:35)");
  }

  await pres.writeFile({ fileName: OUT });
  await applyThemeColors(OUT, THEME);
  if (TRACE) fs.writeFileSync(process.env.DECK_TRACE, JSON.stringify({ size: [13.333, 7.5], theme: THEME, ...TRACE }, null, 1));
  console.log("wrote", OUT);
}

// Write THEME's colours and name into the saved file's theme part (pptxgenjs
// cannot), so scheme colours resolve to this palette instead of Office's stock one.
async function applyThemeColors(file, theme) {
  const JSZip = require("jszip");
  const zip = await JSZip.loadAsync(fs.readFileSync(file), { createFolders: false });
  const part = "ppt/theme/theme1.xml";
  let xml = await zip.file(part).async("string");
  for (const [k, v] of Object.entries(theme.colors)) {
    const re = new RegExp(`<a:${k}>[\\s\\S]*?</a:${k}>`);
    if (!re.test(xml)) throw new Error(`theme part has no <a:${k}>`);
    xml = xml.replace(re, `<a:${k}><a:srgbClr val="${v}"/></a:${k}>`);
  }
  xml = xml.replace(/<a:clrScheme name="[^"]*"/, `<a:clrScheme name="${theme.name}"`);
  zip.file(part, xml);
  // Repairs of what pptxgenjs writes, each a schema violation PowerPoint answers with its repair prompt
  // (checked with the OOXML schemas, scripts/validate_pptx: Apache POI XMLBeans):
  //  - the slide-number placeholder has a fixed id (25) and tables an id of their own, so shapes carry duplicate ids;
  //  - a paragraph of several runs repeats <a:pPr> before every run, where only runs may follow a run;
  //  - a shape may be written with a negative extent (caught here, fixed at the call);
  //  - the notes-master list is written after the slide list in presentation.xml;
  //  - bar charts carry a third <c:axId> without a series axis, and tickLblSkip follows noMultiLvlLbl.
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/(slides|slideLayouts|slideMasters|notesSlides)\/.*\.xml$/.test(n))) {
    let n = 1;
    let x = await zip.file(name).async("string");
    if (/^ppt\/slides\//.test(name)) x = x.replace(/<p:cNvPr id="\d+"/g, () => `<p:cNvPr id="${n++}"`);
    x = x.replace(/<\/a:r>\s*<a:pPr\b[^>]*\/>/g, "</a:r>").replace(/<\/a:r>\s*<a:pPr\b[^>]*>[\s\S]*?<\/a:pPr>/g, "</a:r>");
    const neg = x.match(/<a:ext cx="-?\d+" cy="-?\d+"\/>/g)?.filter((e) => e.includes('"-'));
    if (neg && neg.length) throw new Error(`${name}: negative extent ${neg[0]}`);
    zip.file(name, x);
  }
  {
    let x = await zip.file("ppt/presentation.xml").async("string");
    const m = x.match(/<p:notesMasterIdLst>[\s\S]*?<\/p:notesMasterIdLst>/);
    if (m) x = x.replace(m[0], "").replace("</p:sldMasterIdLst>", "</p:sldMasterIdLst>" + m[0]);
    zip.file("ppt/presentation.xml", x);
  }
  for (const name of Object.keys(zip.files).filter((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n))) {
    let x = await zip.file(name).async("string");
    if (!x.includes("<c:serAx>")) x = x.replace(/(<c:barChart>[\s\S]*?<c:axId val="\d+"\/><c:axId val="\d+"\/>)<c:axId val="\d+"\/>/, "$1");
    x = x.replace(/(<c:noMultiLvlLbl val="\d"\/>)\s*(<c:tickLblSkip val="\d+"\/>)?\s*(<c:tickMarkSkip val="\d+"\/>)?/g, (m0, a, b, c) => (b || "") + (c || "") + a);
    zip.file(name, x);
  }
  // write the package back without directory entries and with the content types first, as PowerPoint does
  const out = new JSZip();
  const names = Object.keys(zip.files).filter((n) => !zip.files[n].dir);
  for (const name of ["[Content_Types].xml", ...names.filter((n) => n !== "[Content_Types].xml")]) out.file(name, await zip.file(name).async("nodebuffer"), { createFolders: false });
  fs.writeFileSync(file, await out.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

main().catch((e) => { console.error(e); process.exit(1); });

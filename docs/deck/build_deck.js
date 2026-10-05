#!/usr/bin/env node
/* Build the ten-minute CIB W78 talk on CrossMEP as a PowerPoint file.

   Inputs:  docs/figures/*.png and docs/figures/deck_data.json, both written by
            scripts/make_figures.py from the released data; the gallery
            screenshot from scripts/screenshot_gallery.js.
   Output:  docs/CrossMEP_CIBW78_talk.pptx (speaker notes = docs/TALK.md)

   Rebuild:
       pip install matplotlib "qrcode[pil]" && python scripts/make_figures.py
       NODE_PATH=$(npm root -g) node scripts/screenshot_gallery.js        # needs Playwright
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
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B0B0B", lt1: "FFFFFF", dk2: "1F2933", lt2: "EEF1F4",
    accent1: "2A78D6", accent2: "EB6834", accent3: "1BAF7A", accent4: "4A3AA7",
    accent5: "E34948", accent6: "008300", hlink: "2A78D6", folHlink: "4A3AA7",
  },
};
const INK2 = "52514E", MUTED = "898781", GRID = "E1E0D9", ICE = "CADCFC";
const CODE_FONT = "Courier New";

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

  function caption(slide, text, box, name = "caption") {
    slide.addText(text, { ...box, fontSize: 11, color: INK2, valign: "top", margin: 0, isTextBox: true, objectName: name });
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
    valAxisLabelColor: INK2, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: GRID, size: 0.75 },
    showLegend: false, showTitle: true, titleFontSize: 12, titleColor: THEME.colors.dk1, titleFontFace: "+mn-lt",
    ...extra,
  });

  const comp = D.composition;
  const CAT = D.catalog, CB = CAT.benchmark;
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
    s.addNotes("Hello, I'm Lavinia Pedrollo from Stanford's Center for Integrated Facility Engineering. This is CrossMEP, joint work with David Gvadzabia, Torben Graeber and Martin Fischer: a dataset of the problems a support designer solves, made for training and testing methods that design MEP supports. (0:00)");
  }

  // ========================================================================= 2 motivation
  pres.addSection({ title: "Motivation" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("Every pipe, duct and tray hangs from a support designed by hand", { placeholder: "title" });
    tile(s, 0.6, 1.55, 3.9, 1.5, "≈ 10,000", "support assemblies in one 200,000 sq ft hospital");
    tile(s, 0.6, 3.2, 3.9, 1.5, "20 min – 2 h", "to design each one by hand, from the coordinated model");
    tile(s, 0.6, 4.85, 3.9, 1.5, "≈ ¼", "of all MEP design effort; on the order of $600K of engineering per project");
    caption(s, "Approximate practitioner estimates.", { x: 0.6, y: 6.45, w: 3.9, h: 0.3 }, "estimates note");
    const img = fitImage(s, path.join(FIG, "paper_fig1_route_to_section.png"), { x: 4.9, y: 1.55, w: 7.83, h: 2.4 }, "route to section");
    caption(s, "Support design starts after coordination. At each hanger location the designer works from the section across the run: what passes, how big, how heavy, how far apart, what it hangs from.",
      { x: 4.9, y: img.y + img.h + 0.15, w: 7.83, h: 0.75 }, "fig1 caption");
    panel(s, 4.9, 4.85, 7.83, 1.5, "quote card");
    s.addText([{ text: "Nobody designs a support from the whole model; it is designed from the section at that hanger.", options: { italic: true, breakLine: true } },
      { text: "That section is the unit of work — and the unit of CrossMEP.", options: { bold: true } }],
      { x: 5.2, y: 5.0, w: 7.23, h: 1.2, fontSize: 15, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "quote" });
    s.addNotes("Every pipe, duct and tray in a building hangs from a support assembly: anchors, rods, channel, clamps. On a 200,000 square-foot hospital that is on the order of 10,000 assemblies, each taking 20 minutes to two hours by hand - together roughly a quarter of the MEP design effort. These are practitioner estimates. The work starts after coordination: at every hanger location the designer takes the section across the run and designs a support for exactly what passes through it. That section is the unit of work, and it is the unit of our dataset. (0:15)");
  }

  // ========================================================================= 3 gap + at a glance
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("There was no public dataset of support-design problems", { placeholder: "title" });
    s.addText("Why it has to be synthetic", { x: 0.6, y: 1.5, w: 5.4, h: 0.4, fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "why heading" });
    const reasons = [
      ["Scarcity", "FiLock", "Project models are proprietary; the few open ones are not organised around supports and often export no element sizes."],
      ["Coverage", "FiLayers", "One project is one narrow slice: one building type, one trade mix. A method tuned to it measures fit to that project."],
      ["Control", "FiSliders", "A seeded generator gives unlimited problems with a known distribution, difficulty by construction and held-out seeds."],
    ];
    for (let i = 0; i < reasons.length; i++) {
      const y = 2.05 + i * 1.5;
      await iconCircle(s, 0.6, y, 0.58, reasons[i][1], i + 1, reasons[i][0]);
      s.addText(reasons[i][0], { x: 1.4, y: y - 0.02, w: 4.6, h: 0.36, fontSize: 15, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "reason " + reasons[i][0] });
      s.addText(reasons[i][2], { x: 1.4, y: y + 0.38, w: 4.6, h: 0.95, fontSize: 12.5, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "reason text " + reasons[i][0] });
    }
    s.addText("CrossMEP at a glance", { x: 6.35, y: 1.5, w: 6.38, h: 0.4, fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "glance heading" });
    const tw = (6.38 - 2 * 0.2) / 3, th = 2.15;
    const tiles = [
      [fmtInt(comp.contexts), "contexts in four splits on disjoint seeds"],
      [fmtInt(comp.elements), "elements: pipes, cable trays, ducts and conduits; six trades"],
      ["C1–C8", "eight difficulty tiers by exact element count"],
      ["0 labels", "the brief, not the answer: no support-assembly information"],
      ["Traced", "every constant from a standard, a manufacturer table or a measurement"],
      ["Open", "data CC BY 4.0, code MIT; a seeded, deterministic generator"],
    ];
    tiles.forEach(([big, label], i) => {
      const r = Math.floor(i / 3), c = i % 3;
      tile(s, 6.35 + c * (tw + 0.2), 2.05 + r * (th + 0.2), tw, th, big, label, { bigSize: 26, labelSize: 11.5 });
    });
    s.addNotes("Learning-based methods for this task need many such sections, and none were public. Project models are proprietary, the open ones are not organised around supports, and any one project covers one narrow slice. So we built CrossMEP: 7,000 contexts with about 31,500 elements, stratified into eight tiers, deliberately unlabeled, with every constant traced to its source, checked against an open IFC project, and released openly with the generator. (1:00)");
  }

  // ========================================================================= 4 anatomy
  pres.addSection({ title: "The dataset" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("A context is the section at one hanger: the brief, not the answer", { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "01_what_a_context_is.png"), { x: 0.6, y: 1.45, w: 12.13, h: 4.95 }, "context figure");
    caption(s, "Per element: kind, service and trade · bare size · insulation per side · load per metre × the span it was sized at = load at the support · position along and out from the surface. Per context: slab or wall, substrate, thickness. Absent by design: channel, rods, clamps, anchors — and any “correct” answer, since a feasible support depends on the catalog you build from.",
      { x: 0.6, y: img.y + img.h + 0.1, w: 12.13, h: 0.55 }, "context caption");
    s.addNotes("Here is one context. It is a 2-D section at one support location. Each element carries its kind, service and trade, its bare size, its insulation, its load per metre and the span it was sized at - so the load at this support - and its position along and out from the surface. Plus the surface itself: slab or wall, substrate, thickness. What is not in it is the support: no channel, no rods, no anchors, and no 'correct answer', because a feasible support depends on the catalog you build from. The context is the brief; the assembly is the answer. (1:40)");
  }

  // ========================================================================= 5 generation
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("How a context is generated: rules, not free randomness", { placeholder: "title" });
    const steps = [
      ["Tier.", "Cn fixes the exact element count, n = 1 … 8."],
      ["Surface.", "Ceiling or wall (78 / 22 %); concrete slab or wall, 150–300 mm thick."],
      ["Services.", "Grouped as trades run: hot + cold pairs, flow + return, chilled banks, sprinkler mains, 1–2 trays, ducts, conduit groups of 2–6."],
      ["Rows.", "Bulky first: ducts nearest the surface, then trays and conduits, then pipes."],
      ["Spacing.", "Gaps drawn from gaps measured on a built project (at least 25 mm); stagger within rows; electrical above wet on walls."],
      ["Check.", "Every pair at least 25 mm clear; rows centred; sizes, insulation, loads and positions recorded."],
    ];
    steps.forEach(([head, text], i) => {
      const y = 1.55 + i * 0.86;
      s.addShape(pres.ShapeType.ellipse, { x: 0.6, y: y + 0.04, w: 0.44, h: 0.44, fill: { color: C.accent1 }, objectName: "step circle " + (i + 1) });
      s.addText(String(i + 1), { x: 0.6, y: y + 0.04, w: 0.44, h: 0.44, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "step number " + (i + 1) });
      s.addText([{ text: head + " ", options: { bold: true } }, { text }], { x: 1.25, y: y - 0.1, w: 5.45, h: 0.72, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "step " + (i + 1) });
    });
    const img = fitImage(s, path.join(FIG, "05_generation_example.png"), { x: 6.9, y: 1.5, w: 5.83, h: 4.3 }, "generation example");
    caption(s, "One generated benchmark context, three rows by priority; the gap marked is one draw from the measured distribution. Every context is seeded: the same seed gives the same file, byte for byte.",
      { x: 6.9, y: img.y + img.h + 0.12, w: 5.83, h: 0.75 }, "generation caption");
    s.addNotes("How is a context made? Not by free randomness: by rules you would recognise. The tier fixes the number of elements. We pick the surface. We fill the count with services the way trades actually run - hot and cold together, flow and return together, conduits in groups. Bulky services go nearest the slab: ducts, then containment, then pipes. Gaps between neighbours are drawn from gaps measured on a built project, with a 25 millimetre minimum, plus a small stagger within rows; on walls, electrical stays above water. Finally every context is checked - every pair at least 25 millimetres clear - and it is seeded: the same seed gives the same file, byte for byte. (2:30)");
  }

  // ========================================================================= 6 sources
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("Every number has a source, and every load is computed from it", { placeholder: "title" });
    const hdr = (t) => ({ text: t, options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.dk2 }, fontSize: 12 } });
    const cell = (t, b) => ({ text: t, options: { fontSize: 12, color: THEME.colors.dk1, bold: !!b } });
    const rows = [
      [hdr("Element"), hdr("Sizes"), hdr("Load basis")],
      [cell("Pipes DN15–100", true), cell("EN 10220 / EN 10255 medium series"), cell("steel + water × ASME B31.1 water-service span (published points only)")],
      [cell("Insulation", true), cell("GEG Anlage 8 (heated); 30/50 mm condensation control (chilled)"), cell("—")],
      [cell("Cable trays 150–600", true), cell("IEC 61537 systems"), cell("full tray: 50 kg/m at 300 mm datum, × 2.0 m")],
      [cell("Ducts", true), cell("EN 1505 rectangular; EN 1506 round"), cell("manufacturer duct-weight table incl. flanges, × 2.4 m")],
      [cell("Conduits Ø20–50", true), cell("IEC 61386-1, parallel groups of 2–6"), cell("steel tube + 40 %-of-bore cable fill, × 2.0 m")],
    ];
    s.addTable(rows, { x: 0.6, y: 1.55, w: 7.9, colW: [1.9, 2.8, 3.2], fontFace: THEME.bodyFontFace, fontSize: 12,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: [0.42, 0.78, 0.78, 0.6, 0.6, 0.6], valign: "middle", margin: 0.07, objectName: "sources table" });
    s.addText("Layout conventions", { x: 8.85, y: 1.55, w: 3.9, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "conventions heading" });
    bullets(s, [
      "Bulky services nearest the slab: ducts, then containment, then pipes",
      "Trades run in banks: hot + cold pairs, flow + return, conduit groups",
      "Electrical kept above wet services on walls (drip)",
      "Clear gaps drawn from a distribution measured on a built project; 25 mm minimum",
      "Within-row stagger calibrated to measured elevation spread",
    ], { x: 8.85, y: 2.1, w: 3.9, h: 3.6 }, 13, "conventions");
    panel(s, 0.6, 5.75, 12.13, 0.85, "sources note card");
    s.addText("Every constant carries a source and a status (verified, practice-cited, or a declared design choice) in the repository. Loads are derived in code from those sources, so each number can be traced and checked.",
      { x: 0.9, y: 5.8, w: 11.5, h: 0.75, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "sources note" });
    s.addNotes("Every number in a context has a source. Pipe sizes and walls from EN 10220 and 10255, filled with water, at ASME B31.1 water-service spans. Insulation from the German GEG for heated lines and a condensation-control schedule for chilled water. Trays at IEC 61537 widths, loaded full. Ducts at the EN preferred sizes with a manufacturer weight table. Conduits at IEC 61386 sizes with 40 per cent cable fill. The loads are computed from these sources in the code, and every constant is documented with its source and status. Things that are choices - the trade mix, the tier composition - are labelled as design choices, not presented as measurements. (3:20)");
  }

  // ========================================================================= 7 release
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText(`The release: ${fmtInt(comp.contexts)} contexts in four splits on disjoint seeds`, { placeholder: "title" });
    const hdr = (t, a) => ({ text: t, options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.dk2 }, fontSize: 12, align: a || "right" } });
    const num = (t, b, a) => ({ text: t, options: { fontSize: 12, color: THEME.colors.dk1, bold: !!b, align: a || "right" } });
    const names = { train: "train", val: "validation", test: "test", benchmark: "benchmark" };
    const rows = [[hdr("split", "left"), hdr("contexts"), hdr("elements"), hdr("seed")]];
    let tc = 0, te = 0;
    for (const sp of ["train", "val", "test", "benchmark"]) {
      const v = D.splits[sp];
      tc += v.contexts; te += v.elements;
      rows.push([num(names[sp], false, "left"), num(fmtInt(v.contexts)), num(fmtInt(v.elements)), num(String(v.seed))]);
    }
    rows.push([num("total", true, "left"), num(fmtInt(tc), true), num(fmtInt(te), true), num("")]);
    s.addTable(rows, { x: 0.6, y: 1.55, w: 5.6, colW: [1.7, 1.3, 1.4, 1.2], fontFace: THEME.bodyFontFace, fontSize: 12,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.42, valign: "middle", margin: 0.08, objectName: "splits table" });
    bullets(s, [
      "Tiers assigned round-robin: 625 per tier in train, 125 in the benchmark",
      "Four in five contexts hang from a ceiling, one in five from a wall",
      `Six trades: electrical ${fmtInt(comp.trades.electrical)}, domestic water ${fmtInt(comp.trades.domestic)}, heating ${fmtInt(comp.trades.heating)}, chilled water ${fmtInt(comp.trades.chilled)}, sprinkler ${fmtInt(comp.trades.sprinkler)}, ventilation ${fmtInt(comp.trades.ventilation)} elements`,
      "Plain JSON, with a JSON Schema, Croissant metadata and a datasheet",
    ], { x: 0.6, y: 4.35, w: 5.6, h: 2.35 }, 13, "release facts");
    const kinds = comp.kinds;
    s.addChart(pres.ChartType.bar, [{ name: "elements", labels: ["pipes", "conduits", "cable trays", "ducts"],
      values: [kinds.pipe, kinds.conduit, kinds.cable_tray, kinds.duct] }],
      chartStyle({ x: 6.55, y: 1.5, w: 6.18, h: 2.45, barDir: "bar", barGapWidthPct: 70, catAxisOrientation: "maxMin",
        valAxisHidden: true, valGridLine: { style: "none" }, dataLabelFormatCode: "#,##0",
        title: "Elements by kind, all splits", objectName: "kinds chart" }));
    const dnLabels = Object.keys(comp.dn);
    s.addChart(pres.ChartType.bar, [{ name: "pipes", labels: dnLabels, values: dnLabels.map((k) => comp.dn[k]) }],
      chartStyle({ x: 6.55, y: 4.1, w: 6.18, h: 2.6, barDir: "col", barGapWidthPct: 80, dataLabelFormatCode: "#,##0",
        dataLabelFontSize: 9, valAxisLabelFormatCode: "#,##0", valAxisMinVal: 0, valAxisMaxVal: 4000, valAxisMajorUnit: 1000,
        title: "Pipes by nominal size, all splits", objectName: "dn chart" }));
    s.addNotes("The release has four splits on disjoint seeds: 5,000 contexts for training, 500 for validation, 500 for test, and a 1,000-context benchmark with 125 per tier. 31,484 elements in total - mostly pipes, then conduits, trays and ducts; pipe sizes from DN15 to DN100, mostly small bore, as in the measured project. Four in five contexts hang from a ceiling, one in five from a wall, and electrical containment is the largest trade by count. Everything is plain JSON with a schema, metadata and a datasheet. (4:05)");
  }

  // ========================================================================= 8 gallery
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("Eight difficulty tiers: tier Cn holds exactly n elements", { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "02_tier_gallery.png"), { x: 0.6, y: 1.4, w: 12.13, h: 4.95 }, "tier gallery");
    caption(s, "One benchmark context per tier; dashed rings are insulation. Within a tier, kinds, trades, services, surfaces and stacking all vary, so element count is the one controlled difficulty axis. C1 is the most common support in any building; C8 is a congested rack.",
      { x: 0.6, y: img.y + img.h + 0.1, w: 12.13, h: 0.55 }, "gallery caption");
    s.addNotes("This is what the data looks like: one benchmark context per tier. C1 is a single element - the most common support in any building. By C8 you have eight services on three rows. Within a tier everything else varies - kinds, trades, surfaces and stacking - so the element count is the one controlled difficulty axis. Note the walls: the section rotates, and electrical sits above water. (4:45)");
  }

  // ========================================================================= 9 experiment 1
  pres.addSection({ title: "Experiments" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText("Experiment 1: as the count rises, scenes get tighter and heavier", { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "03_tiers_stats.png"), { x: 0.6, y: 1.45, w: 12.13, h: 4.75 }, "tier statistics");
    caption(s, `Element count is exact by construction, so ordering is checked on congestion: the median closest gap falls from ${Math.round(gapC2)} mm (C2) to ${Math.round(gapC8)} mm (C8) and the median load at the support rises from ${loadC1.toFixed(2)} to ${loadC8.toFixed(2)} kN. The trends are near-monotone; with 125 contexts per tier, neighbouring tiers can swap.`,
      { x: 0.6, y: img.y + img.h + 0.1, w: 12.13, h: 0.6 }, "experiment 1 caption");
    s.addNotes("First experiment: are the tiers actually ordered? The element count is exact by construction, so we look at congestion. The median closest gap between elements falls from 120 mm at C2 to about 60 mm at C8, and the median load at the support rises from 0.1 to 1.7 kilonewtons. The trend is near-monotone - with 125 contexts per tier, neighbouring tiers can swap - so difficulty is carried jointly by count, congestion and load, with count as the controlled axis. (5:20)");
  }

  // ========================================================================= 10 experiment 2
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText("Experiment 2: generated spacing follows a built project", { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "04_gaps_vs_measured.png"), { x: 0.6, y: 1.45, w: 12.13, h: 4.75 }, "gap distributions");
    caption(s, `buildingSMART Duplex Apartment (open IFC): MEP and Plumbing discipline models parsed with IfcOpenShell, 427 and 231 segments. Measured gaps are irregular, not modular. The two discipline models of the same building are ${Math.round(real)} mm apart; the generated gaps are ${Math.round(w1ins)} mm from the measured ones between insulation surfaces (${Math.round(w1bare)} mm between pipe surfaces); a fixed modular gap would be ${Math.round(fixed)} mm away.`,
      { x: 0.6, y: img.y + img.h + 0.1, w: 12.13, h: 0.6 }, "experiment 2 caption");
    s.addNotes("Second experiment: is the spacing realistic? We parsed two discipline models of the open buildingSMART Duplex Apartment with IfcOpenShell and measured the gaps between parallel runs. They are irregular, not modular - the median is about 108 mm. The generator samples a lognormal fitted to those gaps. The distance between generated and measured distributions is 41 mm between insulation surfaces and 68 mm between pipe surfaces; the building's own two discipline models are 50 mm apart, and a fixed modular gap would be 139 mm away. So the generated spacing sits in the range of the variation between two real models of one building. (6:15)");
  }

  // ========================================================================= 11 experiment 3
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText("Experiment 3: a two-size clamp catalog attaches 1 pipe in 9", { placeholder: "title" });
    const sizes = Object.keys(CAT.by_size);
    s.addChart(pres.ChartType.bar, [
      { name: "attachable", labels: sizes, values: sizes.map((k) => CAT.by_size[k].covered) },
      { name: "no size fits", labels: sizes, values: sizes.map((k) => CAT.by_size[k].pipes - CAT.by_size[k].covered) }],
      chartStyle({ x: 0.6, y: 1.45, w: 6.0, h: 3.55, barDir: "col", barGrouping: "stacked", barGapWidthPct: 45,
        chartColors: [THEME.colors.accent1, "CFCDC3"], dataLabelPosition: "ctr", dataLabelFormatCode: "#,##0;;;",
        dataLabelFontSize: 9, dataLabelColor: THEME.colors.dk1, valAxisLabelFormatCode: "#,##0", valAxisMinVal: 0,
        valAxisMaxVal: 600, valAxisMajorUnit: 100, showLegend: true, legendPos: "b", legendFontSize: 10, legendColor: INK2,
        title: "Pipes by nominal size: what the two-size catalog attaches", objectName: "attach by size chart" }));
    const curve = CAT.demand.curve;
    s.addChart(pres.ChartType.bar, [{ name: "best possible share (%)", labels: curve.map((r) => String(r.k)), values: curve.map((r) => r.pct) }],
      chartStyle({ x: 6.75, y: 1.45, w: 5.98, h: 3.55, barDir: "col", barGapWidthPct: 45, dataLabelFormatCode: "0",
        dataLabelFontSize: 9, valAxisLabelFormatCode: "0", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 20,
        showCatAxisTitle: true, catAxisTitle: `number of clamp sizes, each fitting a ${CAT.demand.width_mm} mm diameter window`,
        catAxisTitleFontSize: 10, catAxisTitleColor: INK2,
        title: "Best share of pipes (%) that any k clamp sizes could attach", objectName: "demand chart" }));
    const tw = (12.13 - 2 * 0.2) / 3;
    const k2 = curve.find((r) => r.k === 2).pct, k6 = curve.find((r) => r.k === 6).pct;
    tile(s, 0.6, 5.1, tw, 1.6, `${fmt1(CB.pct_pipes)} %`,
      `of benchmark pipes attachable with the paper’s two sizes (95 % CI ${fmt1(CB.ci[0])}–${fmt1(CB.ci[1])}); every one is DN40`, { labelSize: 11 });
    tile(s, 0.6 + tw + 0.2, 5.1, tw, 1.6, `${fmt1(k2)} %`,
      `with two sizes placed where the pipes are; ${Math.round(k6)} % with six, and every pipe with ${curve.length}`, { labelSize: 11 });
    tile(s, 0.6 + 2 * (tw + 0.2), 5.1, tw, 1.6, `0 of ${fmtInt(CB.not_pipe)}`,
      `trays, ducts and conduits: a pipe-clamp catalog defines no attachment. Load never binds (${CB.max_pipe_load_kN.toFixed(2)} vs ${CB.min_bin_capacity_kN.toFixed(1)} kN)`, { labelSize: 11 });
    s.addNotes(`The third experiment connects the dataset to the task it serves: what must a catalog of clamps cover? Take the two-size catalog from the paper as an illustration. It attaches ${fmt1(CB.pct_pipes)} per cent of the pipes - ${CB.covered} of ${fmtInt(CB.pipes)}, interval ${Math.round(CB.ci[0])} to ${Math.round(CB.ci[1])} - and every one is a single size, DN40. Load never binds: the heaviest pipe is ${CB.max_pipe_load_kN.toFixed(2)} kilonewtons against a ${CB.min_bin_capacity_kN.toFixed(1)} kilonewton clamp. Trays, ducts and conduits are not covered at all. On the right is what the dataset asks of any catalog: two sizes placed where the pipes are would attach ${Math.round(k2)} per cent, six sizes ${Math.round(k6)}, and ${curve.length} sizes every pipe. So 'what should the catalog contain' becomes a measurement. (7:05)`);
  }

  // ========================================================================= 12 using it
  pres.addSection({ title: "Use" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Use" });
    s.addText("Using CrossMEP: load, filter, generate, inspect", { placeholder: "title" });
    codeCard(s, [
      "import crossmep.tasks as cm",
      "data = cm.load(\"benchmark\")  # 1,000 contexts",
      "cm.filter_contexts(data, pipes=2, trays=1)",
      "cm.catalog_coverage(data, my_catalog)",
      "",
      "from crossmep import generate_custom",
      "generate_custom(100, pipes=(2, 4), trays=1)",
    ], { x: 0.6, y: 1.55, w: 6.0, h: 2.05 }, 13, "code");
    caption(s, "The loader and metrics need only the Python standard library; the generator needs NumPy. Command line: python -m crossmep.",
      { x: 0.6, y: 3.75, w: 6.0, h: 0.6 }, "code caption");
    const img = fitImage(s, path.join(FIG, "07_gallery_screenshot.png"), { x: 6.95, y: 1.55, w: 5.78, h: 3.1 }, "gallery screenshot");
    caption(s, "Interactive gallery: filter the benchmark by tier, kind, trade and surface.", { x: 6.95, y: img.y + img.h + 0.08, w: 5.78, h: 0.3 }, "gallery screenshot caption");
    const uses = [
      ["Curriculum", "train from C1 to C8, one element at a time"],
      ["Stratified evaluation", "success and feasibility-collapse rate per tier"],
      ["Probes", "held-out seeds and custom compositions"],
    ];
    const uw = (12.13 - 2 * 0.2) / 3;
    uses.forEach(([head, text], i) => {
      const x = 0.6 + i * (uw + 0.2);
      panel(s, x, 5.2, uw, 1.4, "use " + head);
      s.addText(head, { x: x + 0.25, y: 5.32, w: uw - 0.5, h: 0.4, fontSize: 15, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "use head " + head });
      s.addText(text, { x: x + 0.25, y: 5.75, w: uw - 0.5, h: 0.7, fontSize: 12.5, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "use text " + head });
    });
    s.addNotes("Using it takes a few lines. Load a split - the loader needs only the Python standard library - filter by composition, test your own catalog against the benchmark, or generate your own mix with the same rules. There is an interactive gallery for inspection. And because there are no labels, the same files serve reinforcement learning, constraint-programming baselines and human benchmarking: a curriculum over the tiers, per-tier evaluation, and held-out seeds and custom compositions as probes. (7:50)");
  }

  // ========================================================================= 13 scope & next
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Use" });
    s.addText("Scope, and what comes next", { placeholder: "title" });
    const cw = (12.13 - 0.25) / 2;
    panel(s, 0.6, 1.5, cw, 3.55, "scope card");
    s.addText("Scope", { x: 0.9, y: 1.65, w: cw - 0.6, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "scope heading" });
    bullets(s, [
      "One cross-section at one support: routing, branches and elevation changes are outside it; so is support spacing — the span is recorded per element, so a method can vary it",
      "Realism checked on two discipline models of one open residential project; congested racks rest on coordination practice and standards",
      "Trade mix and tier composition are design choices, not survey results",
      "Synthetic: not for the structural design of real installations",
    ], { x: 0.9, y: 2.2, w: cw - 0.6, h: 2.75 }, 14, "scope bullets");
    const x2 = 0.6 + cw + 0.25;
    panel(s, x2, 1.5, cw, 3.55, "next card");
    s.addText("Next", { x: x2 + 0.3, y: 1.65, w: cw - 0.6, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "next heading" });
    bullets(s, [
      "Per-tier feasibility-collapse measurement in a multi-element synthesis environment",
      "Verification against commercial corridor models",
      "An expert plausibility review of generated scenes, and a curated expert reference set for evaluation",
    ], { x: x2 + 0.3, y: 2.2, w: cw - 0.6, h: 2.75 }, 14, "next bullets");
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.3, w: 12.13, h: 1.35, rectRadius: 0.07, fill: { color: C.text2 }, objectName: "ask band" });
    s.addText([{ text: "If you coordinate services or design supports, ", options: { bold: true } },
      { text: "open the gallery, filter for the scenes you know, and tell us what looks wrong. Every rule is one documented constant away from being changed." }],
      { x: 0.95, y: 5.4, w: 10.0, h: 1.15, fontSize: 15, color: C.background1, valign: "middle", margin: 0, isTextBox: true, objectName: "ask" });
    s.addImage({ path: path.join(FIG, "qr_repo.png"), x: 11.55, y: 5.42, w: 1.1, h: 1.1, objectName: "qr ask" });
    s.addNotes("Its scope: one section at one support - routing, branches and spacing are outside it, although the span is recorded so a method can vary it. Realism is checked on one open residential project; congested racks rest on practice and standards. The trade mix is a design choice, and the data is not for structural design. Next: measuring per-tier feasibility collapse in a multi-element synthesis environment, verification on commercial corridor models, and an expert plausibility review - which is where we would value your eye. (8:40)");
  }

  // ========================================================================= 14 closing
  {
    const s = addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Use" });
    s.addText("CrossMEP: the brief, not the answer", { placeholder: "title" });
    s.addText([
      { text: `${fmtInt(comp.contexts)} support-design problems  ·  every number traced  ·  checked against a built project  ·  open data and code`, options: { breakLine: true } },
      { text: " ", options: { breakLine: true, fontSize: 8 } },
      { text: "Data CC BY 4.0, code MIT.  Not for the structural design of real installations.", options: { fontSize: 13 } },
    ], { placeholder: "body" });
    s.addImage({ path: path.join(FIG, "qr_repo.png"), x: 9.6, y: 2.5, w: 2.3, h: 2.3, objectName: "qr closing" });
    s.addText([{ text: REPO, options: { bold: true, breakLine: true } }, { text: "laviniap@stanford.edu" }],
      { x: 9.3, y: 4.9, w: 3.4, h: 0.8, fontSize: 12, color: C.background1, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: "closing link" });
    s.addNotes("CrossMEP is the brief, not the answer: 7,000 support-design problems, every number traced to its source, checked against a built project, and open. The QR code takes you to the data, the code and the gallery. Thank you. (9:10)");
  }

  // ========================================================================= appendix
  pres.addSection({ title: "Appendix" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
    s.addText("Appendix: per-tier statistics, benchmark split", { placeholder: "title" });
    const hdr = (t) => ({ text: t, options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.dk2 }, fontSize: 12, align: "center" } });
    const num = (t) => ({ text: t, options: { fontSize: 12, color: THEME.colors.dk1, align: "center" } });
    const rows = [[hdr("tier"), hdr("contexts"), hdr("median clear gap (mm)"), hdr("median load (kN)"), hdr("median width (mm)")]];
    for (const t of D.tiers) {
      const m = D.tier_medians[t];
      rows.push([num(t), num("125"), num(m.clear_gap_mm == null ? "—" : String(Math.round(m.clear_gap_mm))), num(m.load_kN.toFixed(2)), num(String(Math.round(m.bundle_width_mm)))]);
    }
    s.addTable(rows, { x: 0.6, y: 1.55, w: 7.6, colW: [0.9, 1.2, 2.0, 1.7, 1.8], fontFace: THEME.bodyFontFace, fontSize: 12,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.42, valign: "middle", margin: 0.05, objectName: "tier table" });
    const k = D.kind_totals_benchmark;
    tile(s, 8.5, 1.55, 4.23, 1.2, "4,500 elements", `${fmtInt(k.pipe)} pipes · ${fmtInt(k.conduit)} conduits · ${k.cable_tray} trays · ${k.duct} ducts`, { bigSize: 24, labelSize: 11 });
    tile(s, 8.5, 2.95, 4.23, 1.2, `${Math.round(w1ins)} / ${Math.round(w1bare)} mm`, "Wasserstein-1, generated to measured gaps: insulation / pipe surfaces", { bigSize: 24, labelSize: 11 });
    tile(s, 8.5, 4.35, 4.23, 1.2, `KS p = ${D.fit.ks_p.toFixed(2)}`, `lognormal fit to the measured gaps above 25 mm (n = ${D.fit.n})`, { bigSize: 24, labelSize: 11 });
    s.addNotes("Backup: per-tier medians on the benchmark split, and the fit statistics behind experiment 2.");
  }
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
    s.addText("Appendix: the catalog stress test, with error bars", { placeholder: "title" });
    const hdr = (t, a) => ({ text: t, options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.dk2 }, fontSize: 11, align: a || "center" } });
    const cell = (t, a, b) => ({ text: t, options: { fontSize: 11, color: THEME.colors.dk1, align: a || "center", bold: !!b } });
    const ci = (v) => `${fmt1(v.pct)} (${fmt1(v.lo)}–${fmt1(v.hi)})`;
    const tiers = Object.keys(CB.per_tier);
    const popTiers = CAT.population ? CAT.population.per_tier : {};
    const rowsT = [[hdr("tier"), hdr("pipes"), hdr("benchmark %  (95 % CI)"), hdr("population %  (95 % CI)")]];
    for (const t of tiers) {
      const v = CB.per_tier[t];
      rowsT.push([cell(t), cell(String(v.pipes)), cell(ci(v)), cell(popTiers[t] ? ci(popTiers[t]) : "—")]);
    }
    s.addTable(rowsT, { x: 0.6, y: 1.5, w: 6.4, colW: [0.8, 0.9, 2.35, 2.35], fontFace: THEME.bodyFontFace, fontSize: 11,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.33, valign: "middle", margin: 0.04, objectName: "per tier catalog table" });
    const rowsS = [[hdr("attach diameter rule", "left"), hdr("bins ±0 mm"), hdr("bins ±0.5 mm"), hdr("bins ±1 mm")]];
    for (const rule of ["service", "bare", "insulated"]) {
      const r = CAT.sensitivity.filter((x) => x.rule === rule);
      rowsS.push([cell(rule === "service" ? "service (paper)" : rule, "left", rule === "service"), ...r.map((x) => cell(fmt1(x.pct_benchmark)))]);
    }
    s.addTable(rowsS, { x: 0.6, y: 4.85, w: 6.4, colW: [2.2, 1.4, 1.4, 1.4], fontFace: THEME.bodyFontFace, fontSize: 11,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.33, valign: "middle", margin: 0.04, objectName: "sensitivity table" });
    caption(s, "% of benchmark pipes attachable when both bin edges are widened by the stated amount. DN100 (114.3 mm) lies 0.3 mm above the 108–114 mm bin, so the headline moves with the diameter rule and the edge tolerance.",
      { x: 0.6, y: 6.25, w: 6.4, h: 0.55 }, "sensitivity caption");
    const rowsP = [[hdr("split", "left"), hdr("pipes"), hdr("% attachable (95 % CI)")]];
    for (const [name, v] of Object.entries(CAT.splits)) {
      rowsP.push([cell(name, "left"), cell(fmtInt(v.pipes)), cell(ci({ pct: v.pct, lo: v.ci[0], hi: v.ci[1] }))]);
    }
    s.addTable(rowsP, { x: 7.3, y: 1.5, w: 5.43, colW: [1.4, 1.2, 2.83], fontFace: THEME.bodyFontFace, fontSize: 11,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.33, valign: "middle", margin: 0.04, objectName: "split catalog table" });
    bullets(s, [
      `Intervals: cluster bootstrap over contexts (${fmtInt(CAT.settings.n_boot)} resamples), because the elements of one context are correlated`,
      CAT.population ? `Population: ${fmtInt(CAT.population.contexts_per_tier)} freshly generated contexts per tier; overall ${fmt1(CAT.population.overall.pct)} % (95 % CI ${fmt1(CAT.population.overall.lo)}–${fmt1(CAT.population.overall.hi)})` : "",
      "Only size and capacity are tested, so coverage is an upper bound on what can be installed",
      "Best possible share with k sizes: exact optimum over the distinct attach diameters",
    ].filter(Boolean), { x: 7.3, y: 3.4, w: 5.43, h: 3.3 }, 12, "stress method bullets");
    s.addNotes("Backup for questions on experiment 3. Per tier, the benchmark has only 125 contexts, so its intervals are wide; the population estimate from two thousand generated contexts per tier shows the tiers are about equal. The headline depends on the attach-diameter rule and on bin-edge tolerance because one nominal size, DN100, sits 0.3 millimetres outside a bin. Only size and capacity are tested - clearance, insert orientation and anchors are not - so the coverage is an upper bound on what can be installed.");
  }
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
    s.addText("Appendix: one record, as stored", { placeholder: "title" });
    codeCard(s, recordLines(D.example_record), { x: 0.6, y: 1.55, w: 8.55, h: 2.8 }, 10.5, "record");
    bullets(s, [
      "Units: millimetres, kilonewtons, metres (span)",
      "Widths are bare; insulation_mm is per side",
      "load_kN = load_kN_per_m × span_m",
      "along_mm, out_mm: position along and out from the surface",
      "level: the generative row (metadata)",
    ], { x: 9.45, y: 1.6, w: 3.28, h: 4.1 }, 13, "record notes");
    s.addNotes("Backup: what one stored context looks like - plain JSON, one object per context.");
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
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const part = "ppt/theme/theme1.xml";
  let xml = await zip.file(part).async("string");
  for (const [k, v] of Object.entries(theme.colors)) {
    const re = new RegExp(`<a:${k}>[\\s\\S]*?</a:${k}>`);
    if (!re.test(xml)) throw new Error(`theme part has no <a:${k}>`);
    xml = xml.replace(re, `<a:${k}><a:srgbClr val="${v}"/></a:${k}>`);
  }
  xml = xml.replace(/<a:clrScheme name="[^"]*"/, `<a:clrScheme name="${theme.name}"`);
  zip.file(part, xml);
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

main().catch((e) => { console.error(e); process.exit(1); });

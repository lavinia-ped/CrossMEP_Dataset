#!/usr/bin/env node
/* Build the ten-minute CIB W78 talk on CrossMEP as a PowerPoint file.

   Inputs:  docs/figures/*.png and docs/figures/deck_data.json, both written by
            scripts/make_figures.py from the released data (with the QR codes of
            the repository and the hosted studio); the gallery screenshot from
            scripts/screenshot_gallery.js; the Generator Studio screenshots
            (08_studio_demo, 09_studio_wall, 10_studio_mix) from
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
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B0B0B", lt1: "FFFFFF", dk2: "1F2933", lt2: "EEF1F4",
    accent1: "2A78D6", accent2: "EB6834", accent3: "1BAF7A", accent4: "4A3AA7",
    accent5: "E34948", accent6: "008300", hlink: "2A78D6", folHlink: "4A3AA7",
  },
};
const INK2 = "52514E", MUTED = "898781", GRID = "E1E0D9", ICE = "CADCFC";
const CODE_FONT = "Courier New";
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
    s.addNotes("Hello everyone, I'm Lavinia Pedrollo, from Stanford. Every pipe, duct and cable tray in a building hangs from a support that an engineer designs by hand, from the section at that spot. We want to teach machines to do some of that work, and the first thing we found missing was data: there was no public set of support-design problems. So, with David Gvadzabia, Torben Graeber and Martin Fischer, we built one. It's called CrossMEP. (0:00)");
  }

  // ========================================================================= 2 the assemblies (from the ISARC 2026 talk)
  pres.addSection({ title: "Motivation" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("A hospital needs about 10,000 support assemblies, each designed by hand", { placeholder: "title" });
    const b = { x: 0.6, y: 1.45, w: 6.6, h: 6.6 * 720 / 1280 };
    s.addImage({ path: path.join(FIG, "isarc_building.jpg"), ...b, objectName: "hospital model" });
    const z = { x: b.x + 0.4567 * b.w, y: b.y + 0.4318 * b.h, w: 0.0982 * b.w, h: 0.1396 * b.h };
    const ins = { x: 7.6, y: 1.95, w: 5.13, h: 5.13 * 728 / 1268 };
    const orange = { color: THEME.colors.accent2, width: 1.5 };
    s.addShape(pres.ShapeType.rect, { ...z, fill: { type: "none" }, line: orange, objectName: "zoom box" });
    s.addShape(pres.ShapeType.line, { x: z.x + z.w, y: z.y, w: ins.x - z.x - z.w, h: ins.y - z.y, line: orange, flipV: ins.y < z.y, objectName: "zoom line top" });
    s.addShape(pres.ShapeType.line, { x: z.x + z.w, y: z.y + z.h, w: ins.x - z.x - z.w, h: ins.y + ins.h - z.y - z.h, line: orange, objectName: "zoom line bottom" });
    s.addImage({ path: path.join(FIG, "isarc_ssa.jpg"), ...ins, objectName: "one assembly" });
    s.addShape(pres.ShapeType.rect, { ...ins, fill: { type: "none" }, line: orange, objectName: "inset frame" });
    s.addText("1 unit = 1 structural support assembly (SSA)", { x: ins.x, y: 1.45, w: ins.w, h: 0.45, fontSize: 15, bold: true, color: C.text1, valign: "bottom", margin: 0, isTextBox: true, objectName: "inset label" });
    const tw = (12.13 - 2 * 0.2) / 3;
    tile(s, 0.6, 5.35, tw, 1.3, "≈ 10,000", "support assemblies in one 200,000 sq ft hospital", { bigSize: 28 });
    tile(s, 0.6 + tw + 0.2, 5.35, tw, 1.3, "20 min – 2 h", "of engineering for each assembly, designed one by one", { bigSize: 28 });
    tile(s, 0.6 + 2 * (tw + 0.2), 5.35, tw, 1.3, "≈ ¼", "of MEP design effort; on the order of $600K per project", { bigSize: 28 });
    caption(s, "Approximate practitioner estimates.", { x: 0.6, y: 6.7, w: 6.0, h: 0.25 }, "estimates note");
    s.addNotes("Here's what that looks like. In this hospital, every red mark is a place where pipes, ducts or cable trays hang from the structure. A modular support system groups several services onto one prefabricated frame, installed as a single unit: a structural support assembly. A hospital of two hundred thousand square feet needs about ten thousand of them. Each takes twenty minutes to two hours to design by hand, roughly a quarter of the whole MEP design effort. These are practitioner estimates. (0:30)");
  }

  // ========================================================================= 3 the synthesis problem (from the ISARC 2026 talk)
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("Synthesizing an assembly from a catalog and a section has resisted automation", { placeholder: "title" });
    panel(s, 0.6, 1.5, 5.7, 2.85, "problem card");
    s.addText([
      { text: "The synthesis problem", options: { bold: true, fontSize: 17, breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Given ", options: { bold: true } }, { text: "a fixed catalog of components and the MEP context: the services crossing the hanger and the surface they hang from.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Find ", options: { bold: true } }, { text: "a feasible assembly that carries the services to the structure.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Tools coordinate the model and check a design; choosing the topology and the parts is still done by hand.", options: { italic: true } },
    ], { x: 0.85, y: 1.65, w: 5.2, h: 2.6, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "problem" });
    const img = fitImage(s, path.join(FIG, "paper_fig1_route_to_section.png"), { x: 6.55, y: 1.5, w: 6.18, h: 2.3 }, "route to section");
    caption(s, "Design starts after coordination: at each hanger the designer works from the section across the run, not from the whole model.",
      { x: img.x, y: img.y + img.h + 0.1, w: img.w, h: 0.5 }, "fig1 caption");
    const why = [
      ["Geometric judgment", "Engineers choose an assembly’s topology from experience."],
      ["Rule explosion", "Code, load and material constraints interact across thousands of combinations."],
      ["Catalog volatility", "Catalogs change faster than rule-based systems can be rewritten."],
    ];
    const cw = (12.13 - 2 * 0.2) / 3;
    why.forEach(([h, t], i) => {
      const x = 0.6 + i * (cw + 0.2);
      panel(s, x, 4.65, cw, 1.6, "why " + h);
      s.addText(`${i + 1}. ${h}`, { x: x + 0.25, y: 4.8, w: cw - 0.5, h: 0.42, fontSize: 17, bold: true, color: C.accent1, valign: "middle", margin: 0, isTextBox: true, objectName: "why head " + h });
      s.addText(t, { x: x + 0.25, y: 5.28, w: cw - 0.5, h: 0.9, fontSize: 15, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "why text " + h });
    });
    s.addNotes("So what is the task? At ISARC we defined it like this. You're given a fixed catalog of components and the context: which services cross the hanger, and what they hang from. You must find a feasible assembly that carries them to the structure. Designers don't work from the whole model. They work from one section at each hanger, like this one. Today's tools coordinate and check; choosing the layout and the parts is still manual. That section is the unit of this work, and the unit of our dataset. (1:05)");
  }

  // ========================================================================= 4 what a method would look like (unpublished work: the approach is a black box)
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("One section in, verified supports out: learnable, given problems to learn from", { placeholder: "title" });
    const Y = 1.7, H = 2.45, MID = Y + H / 2;
    const text = (box, head, body, headColor, bodyColor, name, headSize = 14, bodySize = 11.5) =>
      s.addText([{ text: head, options: { bold: true, fontSize: headSize, color: headColor, breakLine: true } },
                 { text: body, options: { fontSize: bodySize, color: bodyColor } }],
        { ...box, valign: "middle", align: "center", margin: 0.08, isTextBox: true, objectName: "text " + name });
    const arrow = (x0, x1, y, name, opts = {}) =>
      s.addShape(pres.ShapeType.line, { x: Math.min(x0, x1), y, w: Math.abs(x1 - x0), h: 0,
        line: { color: INK2, width: 1.25, ...(x1 > x0 ? { endArrowType: "triangle" } : { beginArrowType: "triangle" }), ...opts }, objectName: "arrow " + name });
    const label = (x, y, w, t, name, color = INK2) =>
      s.addText(t, { x, y, w, h: 0.26, fontSize: 10.5, color, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "label " + name });

    // inputs
    const IX = 0.6, IW = 1.9;
    s.addShape(pres.ShapeType.roundRect, { x: IX, y: Y, w: IW, h: 1.05, rectRadius: 0.06, fill: { color: C.background2 }, line: { color: INK2, width: 1 }, objectName: "box context" });
    text({ x: IX, y: Y, w: IW, h: 1.05 }, "Context", "structure, services, loads", C.text1, INK2, "context");
    s.addShape(pres.ShapeType.can, { x: IX + 0.1, y: Y + H - 1.15, w: IW - 0.2, h: 1.15, fill: { color: C.background2 }, line: { color: INK2, width: 1 }, objectName: "box catalog" });
    text({ x: IX, y: Y + H - 1.05, w: IW, h: 1.0 }, "Catalog", "parts, sizes, unit costs", C.text1, INK2, "catalog");

    // rules
    const RX = 3.0, RW = 2.0;
    s.addShape(pres.ShapeType.roundRect, { x: RX, y: Y, w: RW, h: H, rectRadius: 0.06, fill: { color: C.background2 }, line: { color: THEME.colors.dk2, width: 1.25 }, objectName: "box rules" });
    text({ x: RX, y: Y, w: RW, h: H }, "Rules", "which actions are legal in a state; each action adds parts", C.text1, INK2, "rules");
    arrow(IX + IW, RX, Y + 0.52, "context to rules");
    arrow(IX + IW - 0.1, RX, Y + H - 0.55, "catalog to rules");

    // the approach: a black box
    const BX = 5.6, BW = 2.4;
    s.addShape(pres.ShapeType.roundRect, { x: BX, y: Y, w: BW, h: H, rectRadius: 0.06, fill: { color: THEME.colors.dk1 }, objectName: "black box approach" });
    text({ x: BX, y: Y, w: BW, h: H }, "Approach", "a black box that chooses the next action\n\nrule table · search · learned policy", THEME.colors.lt1, ICE, "approach", 16, 11.5);
    arrow(RX + RW, BX, MID - 0.35, "legal actions");
    label(RX + RW, MID - 0.66, BX - RX - RW, "legal actions", "legal actions");
    arrow(BX, RX + RW, MID + 0.35, "chosen action");
    label(RX + RW, MID + 0.4, BX - RX - RW, "chosen action", "chosen action");

    // verifier and output
    const VX = 8.6, VW = 2.0, OX = 11.05, OW = 1.68;
    s.addShape(pres.ShapeType.roundRect, { x: VX, y: Y, w: VW, h: H, rectRadius: 0.06, fill: { color: "EAF5EE" }, line: { color: THEME.colors.accent6, width: 1.5 }, objectName: "box verifier" });
    text({ x: VX, y: Y, w: VW, h: H }, "Verifier", "judges every finished design: statics, anchors, connectors, buildability", C.text1, INK2, "verifier");
    arrow(BX + BW, VX, MID, "finished design");
    label(BX + BW, MID - 0.31, VX - BX - BW, "finished design", "finished design");
    s.addShape(pres.ShapeType.roundRect, { x: OX, y: Y, w: OW, h: H, rectRadius: 0.06, fill: { color: C.background2 }, line: { color: THEME.colors.dk1, width: 1.5 }, objectName: "box output" });
    text({ x: OX, y: Y, w: OW, h: H }, "Verified designs", "up to ten, ranked by installed cost", C.text1, INK2, "output");
    arrow(VX + VW, OX, MID, "to output");

    // feedback
    const FY = Y + H + 0.3;
    s.addShape(pres.ShapeType.line, { x: VX + VW / 2, y: Y + H, w: 0, h: 0.3, line: { color: THEME.colors.accent6, width: 1.25, dashType: "dash" }, objectName: "feedback down" });
    s.addShape(pres.ShapeType.line, { x: BX + BW / 2, y: FY, w: VX + VW / 2 - BX - BW / 2, h: 0, line: { color: THEME.colors.accent6, width: 1.25, dashType: "dash" }, objectName: "feedback across" });
    s.addShape(pres.ShapeType.line, { x: BX + BW / 2, y: Y + H, w: 0, h: 0.3, line: { color: THEME.colors.accent6, width: 1.25, dashType: "dash", beginArrowType: "triangle" }, objectName: "feedback up" });
    label(BX + BW / 2 + 0.2, FY + 0.03, VX + VW / 2 - BX - BW / 2 - 0.4, "pass or fail, fed back", "feedback", THEME.colors.accent6);

    // legend
    const legend = [["Input", C.background2, INK2], ["Rules", C.background2, THEME.colors.dk2], ["Approach (black box)", THEME.colors.dk1, THEME.colors.dk1],
                    ["Verifier", "EAF5EE", THEME.colors.accent6], ["Output", C.background2, THEME.colors.dk1]];
    let lx = 0.6;
    const LY = 5.05;
    legend.forEach(([t, fill, line]) => {
      s.addShape(pres.ShapeType.roundRect, { x: lx, y: LY + 0.04, w: 0.3, h: 0.2, rectRadius: 0.04, fill: { color: fill }, line: { color: line, width: 1 }, objectName: "legend swatch " + t });
      s.addText(t, { x: lx + 0.38, y: LY, w: 2.2, h: 0.28, fontSize: 11.5, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "legend " + t });
      lx += 0.38 + t.length * 0.085 + 0.55;
    });

    // what any approach needs
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.55, w: 12.13, h: 1.0, rectRadius: 0.07, fill: { color: C.text2 }, objectName: "needs band" });
    s.addText([
      { text: "Whatever sits in the black box, it needs ", options: { color: THEME.colors.lt1 } },
      { text: "problems to learn from", options: { bold: true, color: THEME.colors.lt1 } }, { text: ", ", options: { color: THEME.colors.lt1 } },
      { text: "a fixed set to compare on", options: { bold: true, color: THEME.colors.lt1 } }, { text: " and ", options: { color: THEME.colors.lt1 } },
      { text: "problems that look like practice", options: { bold: true, color: THEME.colors.lt1 } }, { text: ".", options: { color: THEME.colors.lt1 } },
    ], { x: 0.9, y: 5.55, w: 11.5, h: 1.0, fontSize: 16, valign: "middle", margin: 0, isTextBox: true, objectName: "needs text" });
    s.addNotes("What would a method look like? On the left, the brief: the context, and a catalog of parts with prices. The rules say which actions are legal; each action adds parts. In the middle, a black box chooses the next action: a rule table, a search, or a learned policy. A verifier judges every finished design, statics, anchors, buildability, and feeds pass or fail back. Out come verified designs, ranked by cost. Whatever sits in that black box, it needs problems to learn from, a fixed set to compare on, and problems that look like practice. (1:40)");
  }

  // ========================================================================= 3 gap + at a glance
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
    s.addText("Real designs cover one corner of the design space; CrossMEP covers all of it", { placeholder: "title" });
    // the design space: element count across, kinds and trades up; real designs cluster, the generator covers
    const plot = (x, y, w, h, head, sub, name) => {
      panel(s, x, y, w, h, "space " + name);
      s.addText([{ text: head, options: { bold: true, fontSize: 14, color: C.text1, breakLine: true } }, { text: sub, options: { fontSize: 11.5, color: INK2 } }],
        { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.62, valign: "top", margin: 0, isTextBox: true, objectName: "space head " + name });
      const ax = { x: x + 0.55, y: y + 0.85, w: w - 0.8, h: h - 1.3 };
      s.addShape(pres.ShapeType.line, { x: ax.x, y: ax.y + ax.h, w: ax.w, h: 0, line: { color: INK2, width: 1, endArrowType: "triangle" }, objectName: "x axis " + name });
      s.addShape(pres.ShapeType.line, { x: ax.x, y: ax.y, w: 0, h: ax.h, line: { color: INK2, width: 1, beginArrowType: "triangle" }, objectName: "y axis " + name });
      s.addText("elements at the hanger: 1 … 8", { x: ax.x, y: ax.y + ax.h + 0.03, w: ax.w, h: 0.25, fontSize: 10, color: INK2, align: "center", margin: 0, isTextBox: true, objectName: "x label " + name });
      s.addText("kinds, trades, surface", { x: x + 0.02, y: ax.y, w: 0.5, h: ax.h, fontSize: 10, color: INK2, align: "center", valign: "middle", rotate: 270, margin: 0, isTextBox: true, objectName: "y label " + name });
      return ax;
    };
    const dot = (ax, u, v, color, d, name) => s.addShape(pres.ShapeType.ellipse, { x: ax.x + u * ax.w - d / 2, y: ax.y + (1 - v) * ax.h - d / 2, w: d, h: d, fill: { color }, line: { color: THEME.colors.lt1, width: 0.5 }, objectName: "dot " + name });
    const left = plot(0.6, 1.5, 5.7, 2.3, "The real designs we had", "few, from one kind of project with one trade mix: one corner of the space", "real");
    const cluster = [[0.12, 0.2], [0.18, 0.26], [0.22, 0.17], [0.15, 0.33], [0.27, 0.24], [0.2, 0.12], [0.31, 0.3], [0.09, 0.28], [0.25, 0.36], [0.33, 0.19], [0.17, 0.4], [0.3, 0.1]];
    cluster.forEach(([u, v], i) => dot(left, u, v, THEME.colors.accent2, 0.16, "real " + i));
    s.addShape(pres.ShapeType.ellipse, { x: left.x + 0.02 * left.w, y: left.y + (1 - 0.48) * left.h, w: 0.38 * left.w, h: 0.46 * left.h, fill: { type: "none" }, line: { color: THEME.colors.accent2, width: 1, dashType: "dash" }, objectName: "real cluster ring" });
    s.addText("a method tuned here measures fit to that project", { x: left.x + 0.44 * left.w, y: left.y + 0.25 * left.h, w: 0.55 * left.w, h: 0.5, fontSize: 11, color: INK2, italic: true, margin: 0, isTextBox: true, objectName: "real note" });
    const right = plot(0.6, 3.95, 5.7, 2.3, "CrossMEP", "the space filled by construction: uniform over the tiers, or any mix you ask for (generate_custom)", "synthetic");
    for (let i = 0; i < 8; i++) for (let j = 0; j < 4; j++) dot(right, 0.08 + i * 0.125, 0.12 + j * 0.26, C.accent1, 0.13, `syn ${i}${j}`);
    s.addText("CrossMEP at a glance", { x: 6.35, y: 1.5, w: 6.38, h: 0.4, fontSize: 16, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "glance heading" });
    const tw = (6.38 - 2 * 0.2) / 3, th = 2.15;
    const tiles = [
      [fmtInt(comp.contexts), "contexts in four splits on disjoint seeds"],
      [fmtInt(comp.elements), "elements: pipes, cable trays, ducts and conduits; six trades"],
      ["C1–C8", "eight difficulty tiers by exact element count"],
      ["0 labels", "the brief, not the answer: no support-assembly information"],
      ["Traced", "every constant with its source, or declared a design choice"],
      ["Open", "data CC BY 4.0, code MIT; a seeded, deterministic generator"],
    ];
    tiles.forEach(([big, label], i) => {
      const r = Math.floor(i / 3), c = i % 3;
      tile(s, 6.35 + c * (tw + 0.2), 2.05 + r * (th + 0.2), tw, th, big, label, { bigSize: 26, labelSize: 11.5 });
    });
    s.addNotes("Here is the idea behind CrossMEP. The real designs we had were few, and they sat in one corner of the design space: one kind of project, one trade mix. A method tuned to them measures fit to that project, and project models are proprietary anyway. So we generate. CrossMEP covers the space by construction: uniform over the tiers, or shaped to whatever mix you ask for. Seven thousand contexts in eight tiers, deliberately unlabeled, every constant sourced or declared, and all of it open. (2:20)");
  }

  // ========================================================================= 4 anatomy
  pres.addSection({ title: "The dataset" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("We generate what a designer receives: the section at one hanger", { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "01_what_a_context_is.png"), { x: 0.6, y: 1.45, w: 12.13, h: 4.95 }, "context figure");
    caption(s, "Per element: kind, service and trade · bare size · insulation per side · load per metre × the span it was sized at = load at the support · position along and out from the surface. Per context: slab or wall, substrate, thickness. Absent by design: channel, rods, clamps, anchors — and any “correct” answer, since a feasible support depends on the catalog you build from.",
      { x: 0.6, y: img.y + img.h + 0.1, w: 12.13, h: 0.55 }, "context caption");
    s.addNotes("Here's one context: a two-dimensional section at one support location. Each element has its kind, service and trade, its size, its insulation, and its load, which is weight per metre times the span it was sized at, plus its position. Add the surface, a slab or a wall, and that's all. What you won't find is the support: no channel, no rods, no anchors, and no correct answer, because a feasible support depends on the catalog you build from. The context is the brief. The assembly is the answer. (2:55)");
  }

  // ========================================================================= 5 generation
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("Sections follow trade practice and measured spacing, not random shapes", { placeholder: "title" });
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
    s.addNotes("How do we make a context? Not by free randomness, but by rules an engineer would recognize. The tier fixes how many elements there are. We pick the surface and fill it the way trades really run services: hot and cold together, flow and return together, conduits in groups, bulky services nearest the slab. Gaps between neighbors are drawn from gaps measured on a built project, never below twenty-five millimeters. On walls, electrical stays above water. Every context is checked, and it's seeded: the same seed gives the same file, byte for byte. (3:35)");
  }

  // ========================================================================= 6 sources
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("Sizes, spans and loads come from standards; the choices are declared", { placeholder: "title" });
    const hdr = (t) => ({ text: t, options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.dk2 }, fontSize: 12 } });
    const cell = (t, b) => ({ text: t, options: { fontSize: 12, color: THEME.colors.dk1, bold: !!b } });
    const rows = [
      [hdr("Element"), hdr("Sizes"), hdr("Load basis")],
      [cell("Pipes DN15–100", true), cell("EN 10220 / EN 10255 medium series"), cell("steel + water × ASME B31.1 water-service span (published points only)")],
      [cell("Insulation", true), cell("GEG Anlage 8 (heated); 30/50 mm condensation control (chilled)"), cell("—")],
      [cell("Cable trays 150–600", true), cell("IEC 61537 systems, NEMA VE 1 widths"), cell("full tray: 50 kg/m at 300 mm datum, × 2.0 m (NEMA VE 1 class span)")],
      [cell("Ducts", true), cell("EN 1505 rectangular; EN 1506 round"), cell("manufacturer duct-weight table incl. flanges, × 2.4 m (SMACNA)")],
      [cell("Conduits Ø20–50", true), cell("IEC 61386-1, parallel groups of 2–6"), cell("steel tube + 40 %-of-bore cable fill, × 2.0 m (IET / BS 7671)")],
    ];
    s.addTable(rows, { x: 0.6, y: 1.55, w: 7.9, colW: [1.9, 2.8, 3.2], fontFace: THEME.bodyFontFace, fontSize: 12,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: [0.42, 0.78, 0.78, 0.6, 0.6, 0.6], valign: "middle", margin: 0.07, objectName: "sources table" });
    s.addText("Layout conventions", { x: 8.85, y: 1.55, w: 3.9, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "conventions heading" });
    bullets(s, [
      "Bulky services nearest the slab: ducts, then containment, then pipes",
      "Trades run in banks: hot + cold pairs, flow + return, conduit groups",
      "Electrical kept above wet services on walls (drip; BS 7671 528.3.2)",
      "Clear gaps drawn from a distribution measured on a built project; 25 mm minimum",
      "Within-row stagger calibrated to measured elevation spread",
    ], { x: 8.85, y: 2.1, w: 3.9, h: 3.6 }, 13, "conventions");
    panel(s, 0.6, 5.75, 12.13, 0.85, "sources note card");
    s.addText("Three kinds of ground: standards (what each element is and weighs), measured open buildings (how close neighbours sit) and declared design choices (trade mix, surface mix, number of rows). Every constant carries its source and status in the repository, and the log says why each standard was chosen over its alternatives.",
      { x: 0.9, y: 5.8, w: 11.5, h: 0.75, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "sources note" });
    s.addNotes("Where do the numbers come from? Three places. Sizes, weights and spans come from standards: European steel pipe and duct standards, IEC for conduits and trays, ASME for spans, the German GEG for insulation. How close neighbors sit comes from measured open buildings. And a few things are simply our choices, like the trade mix, and we label them that way. Loads are computed in code from all of this. (4:10)");
  }

  // ========================================================================= 7 release
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText(`${fmtInt(comp.contexts)} contexts in four splits; the test seeds are never trained on`, { placeholder: "title" });
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
    s.addNotes("The release has four splits on disjoint seeds, so a method is never tested on what it trained on: five thousand contexts for training, five hundred each for validation and test, and a benchmark of one thousand, a hundred and twenty-five per tier. Everything is plain JSON with a schema and a datasheet. (4:40)");
  }

  // ========================================================================= 8 gallery
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("Difficulty is one number: tier Cn holds exactly n elements", { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "02_tier_gallery.png"), { x: 0.6, y: 1.4, w: 12.13, h: 4.95 }, "tier gallery");
    caption(s, "One benchmark context per tier; dashed rings are insulation. Within a tier, kinds, trades, services, surfaces and stacking all vary, so element count is the one controlled difficulty axis. C1 is the most common support in any building; C8 is a congested rack.",
      { x: 0.6, y: img.y + img.h + 0.1, w: 12.13, h: 0.55 }, "gallery caption");
    s.addNotes("Here's one benchmark context per tier. C1 is a single element, the most common support in any building. By C8 you have eight services on three rows. Within a tier everything else varies: kinds, trades, surfaces, stacking. So the element count is the one controlled axis of difficulty. And notice the walls: the section rotates, and electrical sits above water. (5:05)");
  }

  // ========================================================================= 9 experiment 1
  pres.addSection({ title: "Experiments" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText("Higher tiers are heavier and tighter, as designed", { placeholder: "title" });
    const img = await cropImage(s, path.join(FIG, "03_tiers_stats.png"), { x: 0.6, y: 1.45, w: 12.13, h: 4.7 }, { x: 0, y: 0, w: 2000, h: 715 }, "tier statistics", "top");
    const pg = TR.population.clear_gap_mm.per_tier;
    caption(s, `A check that the dataset behaves as designed: the tier fixes the element count; load and congestion follow from the rules. Boxes: benchmark, 125 contexts per tier (IQR, whiskers 1.5 IQR); diamonds: medians of ${fmtInt(TR.settings.per_tier)} generated contexts per tier. Load rises with the tier (rank correlation ${rho(TR.benchmark.load_kN.spearman)}; the population medians rise at every step) and the closest gap narrows at every step (${rho(TR.benchmark.clear_gap_mm.spearman)}; ${mm(pg.C2.median)} → ${mm(pg.C8.median)} mm in the population).`,
      { x: 0.6, y: img.y + img.h + 0.12, w: 12.13, h: 0.8 }, "experiment 1 caption", 12.5);
    s.addNotes(`Now three analyses. The first is a design check, not a discovery: does difficulty grow with the tier? The count is fixed by construction, and load and congestion follow from the rules, so this shows the dataset behaves as designed. The load at the support rises with the tier, from about ${loadC1.toFixed(1)} to ${loadC8.toFixed(1)} kilonewtons. The closest gap narrows at every step, from ${Math.round(gapC2)} to about ${Math.round(gapC8)} millimeters. So: report methods tier by tier. (5:30)`);
  }

  // ========================================================================= 10 experiment 2
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText("Spacing holds up on a clinic the generator never saw", { placeholder: "title" });
    const img = await cropImage(s, path.join(FIG, "04_gaps_vs_buildings.png"), { x: 0.6, y: 1.45, w: 12.13, h: 4.7 }, { x: 0, y: 0, w: 2120, h: 790 }, "gap distributions", "top");
    const g = SEC.gen_to_real, r = SEC.real_to_real;
    const gc = g.clinic_plumbing[LW];
    caption(s, `The gap distribution was fitted on the duplex; the clinic was held out. Clear gaps between side-by-side pipes, on sections every 250 mm. Clinic (${SEC.measured.clinic_plumbing.pairs} pipe pairs): ${mm(gc.w1)} mm from the generated gaps (95 % CI ${mm(gc.lo)}–${mm(gc.hi)}), more than the ${mm(gc.noise_floor.median)} mm a perfect generator would show, and about as close as the duplex’s own two models are to each other (${mm(r["duplex_mep|duplex_plumbing"][LW].w1)} mm). Models: buildingSMART Duplex Apartment and Medical-Dental Clinic, CC BY 4.0.`,
      { x: 0.6, y: img.y + img.h + 0.12, w: 12.13, h: 0.8 }, "experiment 2 caption", 12.5);
    s.addNotes(`The second analysis is the one the generator could fail. Is the spacing realistic in a building it has never seen? The gap distribution was fitted on a residential duplex. We kept a second open building aside, a medical-dental clinic, cut it into sections every 250 millimeters, the way a context is defined, and measured the gaps between pipes running side by side. On the right, the distances. Generator to clinic: ${mm(gc.w1)} millimeters. That is above the ${mm(gc.noise_floor.median)} a perfect generator would show, so not a perfect match, but about as close as the duplex's own two models are to each other. A fixed 25-millimeter gap would be about ${Math.round(gc.fixed_25mm / 10) * 10} off. (6:00)`);
  }

  // ========================================================================= 11 experiment 3
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Experiments" });
    s.addText(`A two-size catalog attaches 1 pipe in ${Math.round(100 / CB.pct_pipes)}; the dataset shows what to cover`, { placeholder: "title" });
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
      `of benchmark pipes attachable with the paper’s two sizes (95 % CI ${fmt1(CB.ci[0])}–${fmt1(CB.ci[1])}); every one is DN40`, { labelSize: 11 });
    tile(s, 0.6 + tw + 0.2, 5.1, tw, 1.6, `${fmt1(k2)} %`,
      `with two sizes placed where the pipes are; ${Math.round(k6)} % with six, and every pipe with ${curve.length}`, { labelSize: 11 });
    tile(s, 0.6 + 2 * (tw + 0.2), 5.1, tw, 1.6, `0 of ${fmtInt(CB.not_pipe)}`,
      `trays, ducts and conduits: a pipe-clamp catalog defines no attachment. Load never binds (${CB.max_pipe_load_kN.toFixed(2)} vs ${CB.min_bin_capacity_kN.toFixed(1)} kN)`, { labelSize: 11 });
    s.addNotes(`The third analysis is a use of the dataset, not a test of it: what must a catalog of clamps cover? Our paper's two-size catalog attaches ${fmt1(CB.pct_pipes)} percent of the pipes, with an interval of ${Math.round(CB.ci[0])} to ${Math.round(CB.ci[1])}, all one size, DN40. Load is never the limit, and trays, ducts and conduits aren't covered at all. On the right is what the dataset asks of any catalog: two well-placed sizes could attach ${Math.round(k2)} percent, six sizes ${Math.round(k6)}, ${NUMBER_WORDS[curve.length] || curve.length} sizes every pipe. So 'what should the catalog contain' becomes a measurement. (6:45)`);
  }

  // ========================================================================= 12 demo
  pres.addSection({ title: "Use" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Use" });
    s.addText("Set the parameters and the generator returns the designer’s brief", { placeholder: "title" });
    const demo = path.join(FIG, "08_studio_demo.png");
    const bar = await cropImage(s, demo, { x: 0.6, y: 1.4, w: 12.13, h: 0.85 }, { x: 30, y: 16, w: 2660, h: 176 }, "studio parameters", "top");
    const row = bar.y + bar.h + 0.2;
    const dwg = await cropImage(s, demo, { x: 0.6, y: row, w: 8.45, h: 3.4 }, { x: 330, y: 585, w: 1030, h: 400 }, "studio section", "top");
    caption(s, "In: the parameters (tier C7, seed 0). Out: section A–A at the support, as the support designer receives it (scale 1:20), and the same run in 3D. Every section is a stored output of the released generator, with the Python call that reproduces it.",
      { x: 0.6, y: dwg.y + dwg.h + 0.15, w: 8.45, h: 0.8 }, "studio caption", 12.5);
    const x = 9.3, w = 12.73 - x;
    const v3 = await cropImage(s, demo, { x, y: row, w, h: 2.6 }, { x: 1700, y: 400, w: 980, h: 700 }, "studio 3D", "top");
    s.addImage({ path: path.join(FIG, "qr_studio.png"), x: x + (w - 1.35) / 2, y: v3.y + v3.h + 0.25, w: 1.35, h: 1.35, objectName: "qr studio" });
    s.addText("Scan to open the studio", { x, y: v3.y + v3.h + 1.65, w, h: 0.3, fontSize: 12, color: INK2, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: "studio link" });
    s.addNotes("Let me show it. This is the Generator Studio. I choose what crosses the hanger, a tier or an exact mix, and a seed. Out comes the section a support designer receives, drawn the way an engineer would issue it: every service at true size, its level below the slab, its load, the closest clear gap, and the same run in 3D. Every section is a stored output of the released generator, with the Python call that reproduces it. Scan the code to try it yourself. [Live: switch to the studio, click C3, then Generate another twice, then Exact mix with a duct. If the demo fails, stay on this slide; slide 18 shows two more sections. Before the talk: open the studio once with internet, set its link sharing to public, scan the QR from a phone not logged in.] (7:20)");
  }
  // ========================================================================= 13 using it
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Use" });
    s.addText("Train on the generator, evaluate on the benchmark, report per tier", { placeholder: "title" });
    codeCard(s, [
      "import crossmep.tasks as cm",
      "data = cm.load(\"benchmark\")  # 1,000 contexts",
      "cm.filter_contexts(data, pipes=2, trays=1)",
      "",
      "from crossmep.evaluate import score, compare",
      "score(my_results, data)  # per tier, 95 % CI",
      "compare(mine, baseline, data)  # paired test",
    ], { x: 0.6, y: 1.55, w: 6.0, h: 2.05 }, 13, "code");
    caption(s, "Loading, metrics and scoring need only the Python standard library; the generator needs NumPy. Command line: python -m crossmep generate | validate | evaluate.",
      { x: 0.6, y: 3.75, w: 6.0, h: 0.6 }, "code caption");
    const galleryFile = path.join(FIG, "07_gallery_screenshot.png");
    const galleryH = (await sharp(galleryFile).metadata()).height;          // the filter bar and the first cards sit at the bottom
    const img = await cropImage(s, galleryFile, { x: 6.95, y: 1.55, w: 5.78, h: 3.1 }, { x: 0, y: Math.max(0, galleryH - 800), w: 1370, h: Math.min(800, galleryH) }, "gallery screenshot");
    caption(s, "Interactive gallery: filter the benchmark by tier, kind, trade and surface.", { x: img.x, y: img.y + img.h + 0.08, w: img.w, h: 0.3 }, "gallery screenshot caption");
    const uses = [
      ["Train", "on the generator: unlimited seeds, a curriculum from C1 up to C8"],
      ["Evaluate", "on the benchmark: 125 held-out contexts per tier, the same for every method"],
      ["Report", "per tier with 95 % intervals, paired tests between methods"],
    ];
    const uw = (12.13 - 2 * 0.2) / 3;
    uses.forEach(([head, text], i) => {
      const x = 0.6 + i * (uw + 0.2);
      panel(s, x, 5.2, uw, 1.4, "use " + head);
      s.addText(head, { x: x + 0.25, y: 5.32, w: uw - 0.5, h: 0.4, fontSize: 15, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "use head " + head });
      s.addText(text, { x: x + 0.25, y: 5.75, w: uw - 0.5, h: 0.7, fontSize: 12.5, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "use text " + head });
    });
    s.addNotes("Using it takes a few lines: load a split, filter by composition, or generate your own mix. Because there are no labels, the same files serve reinforcement learning, constraint programming, and benchmarking people. We ship the scoring too. Train on the generator, from C1 up to C8. Evaluate on the benchmark, the same 125 contexts per tier for every method. Report per tier, with 95 percent intervals and paired tests. (8:35)");
  }

  // ========================================================================= 14 scope & next
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Use" });
    s.addText("One section at one support today; a checker and real data come next", { placeholder: "title" });
    const cw = (12.13 - 0.25) / 2;
    panel(s, 0.6, 1.5, cw, 3.55, "scope card");
    s.addText("Scope", { x: 0.9, y: 1.65, w: cw - 0.6, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "scope heading" });
    bullets(s, [
      "One cross-section at one support: routing, branches and elevation changes are outside it; so is support spacing — the span is recorded per element, so a method can vary it",
      "Realism checked on sections of two open buildings, a residential duplex and a medical clinic; congested racks rest on coordination practice and standards",
      "Trade mix and tier composition are design choices, not survey results",
      "Synthetic: not for the structural design of real installations",
    ], { x: 0.9, y: 2.2, w: cw - 0.6, h: 2.75 }, 14, "scope bullets");
    const x2 = 0.6 + cw + 0.25;
    panel(s, x2, 1.5, cw, 3.55, "next card");
    s.addText("Next", { x: x2 + 0.3, y: 1.65, w: cw - 0.6, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "next heading" });
    bullets(s, [
      "A public checker for support designs, with best-known costs from an exact solver on the small tiers",
      "The catalog as an input: generated catalogs, and tests on catalogs a method has never seen",
      "A real test set: sections from commercial projects with supports designed by engineers",
    ], { x: x2 + 0.3, y: 2.2, w: cw - 0.6, h: 2.75 }, 14, "next bullets");
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.3, w: 12.13, h: 1.35, rectRadius: 0.07, fill: { color: C.text2 }, objectName: "ask band" });
    s.addText([{ text: "If you coordinate services or design supports, ", options: { bold: true } },
      { text: "open the gallery, filter for the scenes you know, and tell us what looks wrong. Every rule is one documented constant away from being changed." }],
      { x: 0.95, y: 5.4, w: 10.0, h: 1.15, fontSize: 15, color: C.background1, valign: "middle", margin: 0, isTextBox: true, objectName: "ask" });
    s.addImage({ path: path.join(FIG, "qr_repo.png"), x: 11.55, y: 5.42, w: 1.1, h: 1.1, objectName: "qr ask" });
    s.addNotes("A word on scope. CrossMEP is one section at one support. Pipe spacing was checked on two open buildings; the rest rests on practice and standards, and the trade mix is a design choice. It's not for structural design of real installations. Next: a public checker, with best-known costs, so we can compare methods on the answer; the catalog as an input; and a real test set from commercial projects, with supports designed by engineers. That's where I'd value your eye. (9:00)");
  }

  // ========================================================================= 15 closing
  {
    const s = addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Use" });
    s.addText("Support design now has open problems to learn from", { placeholder: "title" });
    s.addText([
      { text: `${fmtInt(comp.contexts)} support-design problems  ·  every constant sourced or declared`, options: { breakLine: true } },
      { text: "pipe gaps checked on two open buildings  ·  open data and code", options: { breakLine: true } },
      { text: " ", options: { breakLine: true, fontSize: 8 } },
      { text: "Data CC BY 4.0, code MIT.  Not for the structural design of real installations.", options: { fontSize: 13 } },
    ], { placeholder: "body" });
    s.addImage({ path: path.join(FIG, "qr_repo.png"), x: 9.6, y: 2.5, w: 2.3, h: 2.3, objectName: "qr closing" });
    s.addText([{ text: REPO, options: { bold: true, breakLine: true } }, { text: "laviniap@stanford.edu" }],
      { x: 9.3, y: 4.9, w: 3.4, h: 0.8, fontSize: 12, color: C.background1, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: "closing link" });
    s.addNotes("To sum up: CrossMEP is the brief, not the answer. Seven thousand support-design problems, every constant sourced or declared a design choice, pipe spacing checked on two open buildings, and all of it open. If you coordinate services or design supports, try the studio and tell me what looks wrong. Thank you. (9:35)");
  }

  // ========================================================================= appendix
  pres.addSection({ title: "Appendix" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });   // backup for the live demo
    s.addText("A wall with six pipes, and a slab with a duct, a tray and conduits", { placeholder: "title" });
    const cw = (12.13 - 0.25) / 2;
    const a = await cropImage(s, path.join(FIG, "09_studio_wall.png"), { x: 0.6, y: 1.45, w: cw, h: 4.7 }, { x: 690, y: 95, w: 1060, h: 1340 }, "studio wall sheet", "top");
    const b = await cropImage(s, path.join(FIG, "10_studio_mix.png"), { x: 0.6 + cw + 0.25, y: 1.45, w: cw, h: 4.7 }, { x: 590, y: 160, w: 1430, h: 1290 }, "studio mix sheet", "top");
    caption(s, "Tier C6, seed 0, section 5: six pipes fixed to a wall; offsets from the wall face, the closest clear gap 25 mm.", { x: a.x, y: a.y + a.h + 0.08, w: a.w, h: 0.5 }, "wall caption");
    caption(s, "Exact mix: 2 pipes, 1 tray, 1 duct, 2 conduits on a slab; levels below the soffit and the load at the support.", { x: b.x, y: b.y + b.h + 0.08, w: b.w, h: 0.5 }, "mix caption");
    s.addNotes("Backup for the live demo. Left: a wall section, six pipes in two rows, each labelled with its size, trade, insulation, offset from the wall and load at the support. Right: an exact mix on a slab, with a duct, a tray, conduits and pipes, their levels below the soffit and the closest clear gap.");
  }

  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
    s.addText(`Median load rises from ${loadC1.toFixed(2)} kN at C1 to ${loadC8.toFixed(2)} kN at C8 as the gap narrows`, { placeholder: "title" });
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
    const gcl = SEC.gen_to_real.clinic_plumbing[LW];
    tile(s, 8.5, 2.95, 4.23, 1.2, `${mm(gcl.w1)} mm`, `Wasserstein-1, generated to measured pipe gaps of the clinic (95 % CI ${mm(gcl.lo)}\u2013${mm(gcl.hi)})`, { bigSize: 24, labelSize: 11 });
    tile(s, 8.5, 4.35, 4.23, 1.2, `${rho(TR.benchmark.clear_gap_mm.spearman)} / ${rho(TR.benchmark.load_kN.spearman)}`, "rank correlation of tier with the closest gap / with the load", { bigSize: 24, labelSize: 11 });
    s.addNotes("Backup: per-tier medians on the benchmark split, the distance to the held-out building, and the trend statistics behind experiment 1.");
  }
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
    s.addText(`Against the clinic the generator is ${mm(SEC.gen_to_real.clinic_plumbing[LW].w1)} mm off; the small duplex is ${span(SEC.gen_to_real.duplex_mep[LW].w1, SEC.gen_to_real.duplex_plumbing[LW].w1).replace("\u2013", " to ")}`, { placeholder: "title" });
    const hdr = (t, a) => ({ text: t, options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.dk2 }, fontSize: 11, align: a || "center" } });
    const cell = (t, a) => ({ text: t, options: { fontSize: 11, color: THEME.colors.dk1, align: a || "center" } });
    const G = SEC.generated, M = SEC.measured;
    const rowsA = [[hdr("pipe gaps", "left"), hdr("pairs"), hdr("sections"), hdr("median (mm)"), hdr("< 25 mm")],
      [cell("generated (benchmark)", "left"), cell(fmtInt(G.pairs)), cell("\u2014"), cell(mm(G.median_mm)), cell(`${Math.round(100 * G.share_below_25mm)} %`)]];
    for (const k of ["clinic_plumbing", "duplex_mep", "duplex_plumbing"]) {
      rowsA.push([cell(MODEL[k], "left"), cell(fmtInt(M[k].pairs)), cell(fmtInt(M[k].sections)), cell(mm(M[k].median_mm)), cell(`${Math.round(100 * M[k].share_below_25mm)} %`)]);
    }
    s.addTable(rowsA, { x: 0.6, y: 1.5, w: 5.9, colW: [2.0, 0.9, 1.0, 1.1, 0.9], fontFace: THEME.bodyFontFace, fontSize: 11,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.34, valign: "middle", margin: 0.04, objectName: "samples table" });
    const ci = (v) => `${mm(v.w1)} (${mm(v.lo)}\u2013${mm(v.hi)})`;
    const rowsB = [[hdr("Wasserstein-1 (mm)", "left"), hdr("by length"), hdr("each pair once"), hdr("noise floor")]];
    for (const k of ["clinic_plumbing", "duplex_mep", "duplex_plumbing"]) {
      const v = SEC.gen_to_real[k];
      rowsB.push([cell(`generated \u2194 ${SHORT[k]}`, "left"), cell(ci(v[LW])), cell(ci(v.unweighted)), cell(mm(v[LW].noise_floor.median))]);
    }
    for (const [pair, v] of Object.entries(SEC.real_to_real)) {
      const [a, b] = pair.split("|");
      rowsB.push([cell(`${SHORT[a]} \u2194 ${SHORT[b]}`, "left"), cell(ci(v[LW])), cell(ci(v.unweighted)), cell("\u2014")]);
    }
    s.addTable(rowsB, { x: 6.75, y: 1.5, w: 5.98, colW: [2.38, 1.25, 1.35, 1.0], fontFace: THEME.bodyFontFace, fontSize: 11,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.34, valign: "middle", margin: 0.04, objectName: "distances table" });
    const sens = SEC.sensitivity.map((r) => r.models.clinic_plumbing.w1_weighted);
    bullets(s, [
      "Sections every 250 mm; runs within 400 mm of height form a row; gaps between bare pipe surfaces, below 600 mm",
      `Robust: across ${SEC.sensitivity.length} settings of the cut (spacing, row band, axis tolerance, run length) generated \u2194 clinic stays at ${span(Math.min(...sens), Math.max(...sens))} mm`,
      "Noise floor: the distance a perfect generator would still show at that sample size",
      "The duplex samples are small, hence the wide intervals",
    ], { x: 0.6, y: 3.45, w: 5.9, h: 3.2 }, 12.5, "realism bullets");
    caption(s, "Intervals: 95 % bootstrap over contexts (generated) and pipe pairs (measured). Models: buildingSMART Duplex Apartment and Medical-Dental Clinic, CC BY 4.0; derived measurements and attribution in verify/measured/.",
      { x: 6.75, y: 4.3, w: 5.98, h: 0.8 }, "distances caption");
    s.addNotes("Backup for questions on experiment 2: sample sizes, both weightings, the noise floor and the sensitivity of the result to the way the sections are cut.");
  }
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
    s.addText("The diameter rule moves catalog coverage more than tier or split does", { placeholder: "title" });
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
    s.addText("A context is stored as plain JSON: elements, sizes, loads, positions", { placeholder: "title" });
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

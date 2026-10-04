#!/usr/bin/env node
/* Build the ten-minute CIB W78 talk as a PowerPoint file.

   Inputs:  docs/TALK.md (structure and notes), docs/figures/*.png and
            docs/figures/deck_data.json (both from scripts/make_figures.py)
   Output:  docs/CrossMEP_CIBW78_talk.pptx

   Rebuild:
       pip install matplotlib "qrcode[pil]" && python scripts/make_figures.py
       npm install pptxgenjs react-icons react react-dom sharp      # anywhere; set NODE_PATH to its node_modules
       node docs/deck/build_deck.js

   The deck is a structured one (theme, named layouts with placeholders,
   sections, speaker notes) so it can be restyled in PowerPoint; the scheme
   colours are written into the theme after pptxgenjs saves the file.
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

// Optional trace of every drawing call (DECK_TRACE=<file>): docs/deck/preview.py
// renders it with metric-conservative fonts when LibreOffice is unavailable.
const TRACE = process.env.DECK_TRACE ? { layouts: {}, slides: [] } : null;
const strip = (k, v) => (k === "data" && typeof v === "string" && v.length > 200 ? "<base64>" : v);

function traced(slide, layoutName) {
  if (!TRACE) return slide;
  const rec = { layout: layoutName, items: [] };
  for (const m of ["addText", "addShape", "addImage", "addChart", "addTable"]) {
    const orig = slide[m].bind(slide);
    slide[m] = (...args) => {
      rec.items.push({ m, args: JSON.parse(JSON.stringify(args, strip)) });
      return orig(...args);
    };
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

function fmt1(x) { return (Math.round(x * 10) / 10).toFixed(1); }
function fmt0(x) { return String(Math.round(x)); }

// --------------------------------------------------------------------------- deck

async function main() {
  const pres = new pptxgen();
  const C = pres.SchemeColor;
  pres.layout = "LAYOUT_WIDE";                    // 13.333 x 7.5 in
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.author = "Lavinia Pedrollo";
  pres.title = "CrossMEP: the support designer's brief, as a dataset";
  pres.subject = "43rd International CIB W78 Conference, New Delhi, 2026";
  pres.company = "Stanford University, CIFE";

  // ---- layouts ------------------------------------------------------------
  const defineLayout = (spec) => { if (TRACE) TRACE.layouts[spec.title] = JSON.parse(JSON.stringify(spec, strip)); pres.defineSlideMaster(spec); };
  const addSlide = (opts) => traced(pres.addSlide(opts), opts.masterName);
  defineLayout({
    title: "TITLE_DARK",
    background: { color: THEME.colors.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.25, w: 7.3, h: 2.3, fontSize: 38, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "subtitle", type: "body", x: 0.7, y: 3.75, w: 7.3, h: 1.1, fontSize: 16, color: ICE, valign: "top", margin: 0 }, text: "" } },
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
    slide.addText(big, { x: x + 0.25, y: y + 0.1, w: w - 0.5, h: h * 0.56, fontSize: opts.bigSize || 34, bold: true,
      color: opts.color || C.accent1, valign: "middle", margin: 0, isTextBox: true, objectName: "value " + label });
    slide.addText(label, { x: x + 0.25, y: y + h * 0.64, w: w - 0.5, h: h * 0.33, fontSize: opts.labelSize || 12, color: INK2,
      valign: "top", margin: 0, isTextBox: true, objectName: "label " + label });
  }

  async function card(slide, { x, y, w, h, heading, body, icon, n, bodySize }) {
    slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "card " + heading });
    const data = icon ? await iconData(icon, THEME.colors.lt1) : null;
    slide.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: y + 0.3, w: 0.62, h: 0.62, fill: { color: C.accent1 }, objectName: "icon ring " + heading });
    if (data) {
      slide.addImage({ data, x: x + 0.43, y: y + 0.43, w: 0.36, h: 0.36, objectName: "icon " + heading });
    } else {
      slide.addText(String(n || ""), { x: x + 0.3, y: y + 0.3, w: 0.62, h: 0.62, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    }
    slide.addText(heading, { x: x + 1.1, y: y + 0.28, w: w - 1.4, h: 0.66, fontSize: 18, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "heading " + heading });
    slide.addText(body, { x: x + 0.3, y: y + 1.15, w: w - 0.6, h: h - 1.4, fontSize: bodySize || 13, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "body " + heading });
  }

  function bullets(slide, items, box, size = 14, name = "bullets") {
    slide.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })),
      { ...box, fontSize: size, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: name });
  }

  function caption(slide, text, box, name = "caption") {
    slide.addText(text, { ...box, fontSize: 11, color: INK2, valign: "top", margin: 0, isTextBox: true, objectName: name });
  }

  const w1v4 = D.w1.v4_insulation.mep, w1v3 = D.w1.v3_insulation.mep, w1bare = D.w1.v4_bare.mep;
  const real = D.w1.real_to_real, fixed = D.w1.fixed_floor_gap;
  const gapC2 = D.tier_medians.C2.clear_gap_mm, gapC8 = D.tier_medians.C8.clear_gap_mm;
  const loadC1 = D.tier_medians.C1.load_kN, loadC8 = D.tier_medians.C8.load_kN;

  // ========================================================================= 1 title
  pres.addSection({ title: "Opening" });
  {
    const s = addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
    s.addText("CrossMEP: the support designer’s brief, as a dataset", { placeholder: "title" });
    s.addText("A tiered synthetic dataset of multi-trade MEP cross-sections for learning-based structural support assembly synthesis", { placeholder: "subtitle" });
    s.addText([
      { text: "Lavinia Pedrollo ¹  ·  David Gvadzabia ²  ·  Torben Graeber ³  ·  Martin Fischer ¹", options: { bold: true, breakLine: true } },
      { text: "¹ Stanford University, CIFE   ² Lafayette College   ³ Hilti AG", options: { breakLine: true, color: ICE } },
      { text: " ", options: { breakLine: true, fontSize: 6 } },
      { text: "43rd International CIB W78 Conference · IT in Construction · New Delhi, 6–8 October 2026", options: { color: ICE } },
    ], { placeholder: "authors" });
    s.addImage({ path: path.join(FIG, "title_art.png"), x: 8.3, y: 1.6, w: 4.6, h: 2.875, objectName: "section art" });
    s.addText("a generated C8 context: eight services, three rows", { x: 8.3, y: 4.55, w: 4.6, h: 0.3, fontSize: 10, color: ICE, align: "right", margin: 0, isTextBox: true, objectName: "art caption" });
    s.addNotes("Every pipe, duct and tray in a building hangs from something. I am going to talk about the piece of information a support designer starts from - and why we turned it into a public dataset. (0:00)");
  }

  // ========================================================================= 2 problem
  pres.addSection({ title: "The problem" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The problem" });
    s.addText("Every pipe, duct and tray hangs from a support designed by hand", { placeholder: "title" });
    tile(s, 0.6, 1.6, 3.9, 1.5, "≈ 10,000", "support assemblies in one 200,000 sq ft hospital");
    tile(s, 0.6, 3.3, 3.9, 1.5, "20 min – 2 h", "to design each one by hand, from the coordinated model");
    tile(s, 0.6, 5.0, 3.9, 1.5, "≈ ¼", "of MEP design effort; on the order of $600K of engineering per project");
    const img = fitImage(s, path.join(FIG, "paper_fig1_route_to_section.png"), { x: 4.9, y: 1.6, w: 7.85, h: 2.4 }, "route to section");
    caption(s, "Support design starts after coordination. At each hanger the brief is a cross-section: what passes, how big, how heavy, how far apart, what it hangs from. (Paper, Figure 1.)",
      { x: 4.9, y: img.y + img.h + 0.15, w: 7.85, h: 0.75 }, "fig1 caption");
    s.addShape(pres.ShapeType.roundRect, { x: 4.9, y: 5.0, w: 7.85, h: 1.5, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "quote card" });
    s.addText([{ text: "“Nobody designs a support from the whole model. You design it from the section at that hanger.”", options: { italic: true, breakLine: true } },
      { text: "That section is the unit of work — and the unit of this dataset.", options: { bold: true } }],
      { x: 5.2, y: 5.15, w: 7.25, h: 1.2, fontSize: 15, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "quote" });
    s.addNotes("A 200,000 sq ft hospital: on the order of 10,000 support assemblies, each 20 minutes to 2 hours by hand; roughly a quarter of MEP design effort. Support design starts AFTER coordination: the designer receives the coordinated model and works hanger by hanger. At each hanger the brief is a cross-section. Nobody designs a support from the whole model - you design it from the section at that hanger. That section is the unit of work, and the unit of our dataset. (0:50)");
  }

  // ========================================================================= 3 why synthetic
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The problem" });
    s.addText("Learning to design supports needs the full spread of sections — not one project", { placeholder: "title" });
    const cw = 3.9, gap = 0.215, y = 1.6, h = 2.95;
    await card(s, { x: 0.6, y, w: cw, h, heading: "Scarcity", icon: "FiDatabase", n: 1,
      body: "Project models are proprietary. The few open ones are not organised around supports and often export no element sizes." });
    await card(s, { x: 0.6 + cw + gap, y, w: cw, h, heading: "Coverage", icon: "FiLayers", n: 2,
      body: "One accessible project is one narrow slice: one building type, one trade mix. A method tuned to it measures fit to that project, not competence on the problem." });
    await card(s, { x: 0.6 + 2 * (cw + gap), y, w: cw, h, heading: "Control", icon: "FiSliders", n: 3,
      body: "A seeded generator yields unlimited sections with a known distribution: difficulty by construction, rare congested racks on demand, held-out seeds for testing." });
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 4.85, w: 12.13, h: 1.3, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "so card" });
    s.addText([{ text: "So: ", options: { bold: true } },
      { text: "a rule-based generator — no learned model, no free randomness — that encodes the conventions you already use, is verified against a built project, and is public. We are not claiming a building; we are claiming the rules, and we show where each rule comes from." }],
      { x: 0.9, y: 4.95, w: 11.5, h: 1.1, fontSize: 15, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "so text" });
    s.addNotes("Automating support design with learning needs MANY of those sections - the full spread of what shows up in buildings, not one project. Project models are proprietary; the few open ones are not organised around supports and often export no sizes. One project is one narrow slice. So: a rule-based generator, no learned model, no free randomness, that encodes the conventions you already use, verified against a built project, and public. We are not claiming a building. We are claiming the rules, and we show where each rule comes from. (1:40)");
  }

  // ========================================================================= 4 what a context is
  pres.addSection({ title: "The dataset" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("A context is the section at one hanger — the brief, not the answer", { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "01_what_a_context_is.png"), { x: 0.6, y: 1.45, w: 12.13, h: 5.0 }, "context figure");
    caption(s, "Per element: kind, service and trade · bare size · insulation per side · load per metre × the span it was sized at = load per support · position. Per context: slab or wall, substrate, thickness. Absent by design: channel, rods, clamps, anchors — and any “correct” answer, because a feasible support depends on the catalog you build from.",
      { x: 0.6, y: img.y + img.h + 0.1, w: 12.13, h: 0.5 }, "context caption");
    s.addNotes("One 2-D section perpendicular to the run at one support location. Each element: kind, service and trade; bare size; insulation per side; load per metre and the span it was sized at, so load per support = kN/m x span; position along the surface and standoff from it. The surface: slab or wall, substrate, thickness. Deliberately absent: channel, rods, clamps, anchors. The context is the brief; the assembly is the answer. There are no 'correct' answers in the files because a feasible support depends on the catalog you build from. If you have ever been handed a section and a catalog and asked to make it hang - that is exactly what is in each record, in millimetres and kN. (2:30)");
  }

  // ========================================================================= 5 sources
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
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 5.75, w: 12.13, h: 0.85, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "sources note card" });
    s.addText("Every constant carries a source and a status (VERIFIED / PRACTICE-CITED / DEFAULT) in the repository. Loads are derived in code from those sources and pinned by tests: disagree with a number, change one line, and one test tells you what moved.",
      { x: 0.9, y: 5.8, w: 11.5, h: 0.75, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "sources note" });
    s.addNotes("Sizes from the standards you use; loads computed from them: EN 10255 steel plus water times B31.1 spans; the published full-tray datum; verbatim manufacturer duct weights; IEC fill for conduits. Layout conventions: ducts nearest the slab, then containment, then pipes; trades run in banks; electrical above wet on walls; clear gaps drawn from a distribution measured on a built project. Every constant has a source and a status in the repo; the loads are computed from those sources in the code, and the tests pin them. If you disagree with a number, there is one line to change and one test that will tell you what moved. (3:20)");
  }

  // ========================================================================= 6 tiers
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "The dataset" });
    s.addText("Eight tiers by element count: from a lone pipe to a congested rack", { placeholder: "title" });
    fitImage(s, path.join(FIG, "02_tiers_examples.png"), { x: 0.6, y: 1.4, w: 12.13, h: 4.25 }, "tier examples");
    tile(s, 0.6, 5.75, 3.9, 1.0, "C1 → C8", "exactly n elements per tier; trades, kinds, surfaces and stacking vary within it", { bigSize: 26, labelSize: 11 });
    tile(s, 4.715, 5.75, 3.9, 1.0, `${fmt0(gapC2)} → ${fmt0(gapC8)} mm`, "median clear gap between elements, C2 to C8 (benchmark split)", { bigSize: 26, labelSize: 11 });
    tile(s, 8.83, 5.75, 3.9, 1.0, `${loadC1.toFixed(2)} → ${loadC8.toFixed(2)} kN`, "median load at the support, C1 to C8", { bigSize: 26, labelSize: 11 });
    s.addNotes("Tier Cn = exactly n elements, C1 to C8; everything else varies within the tier. C1 is the most common support in any building: one pipe, one tray, one duct. C8 is the congested rack. As the count rises the median clear gap falls from 120 mm to 62 mm and the median load at the support rises from 0.10 kN to 1.7 kN. Difficulty here means a tighter, heavier scene - not that the support is harder to calculate. Whether it is harder to SOLVE is for the method to show. (4:10)");
  }

  // ========================================================================= 7 verification
  pres.addSection({ title: "Evidence" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
    s.addText(`Spacing checked against a built project: ${fmt0(w1v4)} mm from the measured model`, { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "04_gaps_vs_measured.png"), { x: 0.6, y: 1.45, w: 12.13, h: 5.05 }, "gap distributions");
    caption(s, `buildingSMART Duplex Apartment, MEP and Plumbing discipline models parsed with IfcOpenShell (427 and 231 segments): sizes, parallel-run counts, elevation spread and clear gaps measured. Gaps are irregular, not modular (median 108 mm, quartiles 24–238). The two real discipline models of the same building are ${fmt0(real)} mm apart; a fixed modular gap would be ${fmt0(fixed)} mm away.`,
      { x: 0.6, y: img.y + img.h + 0.08, w: 12.13, h: 0.5 }, "verification caption");
    s.addNotes("buildingSMART Duplex Apartment, MEP and Plumbing discipline models, parsed with IfcOpenShell: 427 and 231 segments; sizes, parallel-run counts, elevation spread and clear gaps measured. Gaps are irregular, not modular: median 108 mm, quartiles 24 to 238. We fit a lognormal to the measurement and sample from it. Distance between generated and measured gap distributions: 41 mm - the two real discipline models of the SAME building are 50 mm apart; a fixed modular gap would be 139 mm away. The generator sits inside the variation you get between two disciplines' models of one building. That is the realism claim, no more. (5:00)");
  }

  // ========================================================================= 8 honesty
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
    s.addText("What we found preparing the public release — and fixed", { placeholder: "title" });
    fitImage(s, path.join(FIG, "05_v3_vs_v4.png"), { x: 0.6, y: 1.4, w: 12.13, h: 3.05 }, "v3 vs v4");
    const cy = 4.6, ch = 2.05, cw = 5.95;
    s.addShape(pres.ShapeType.roundRect, { x: 0.6, y: cy, w: cw, h: ch, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "card 3.0" });
    s.addText("Revision 3.0 — the paper’s files", { x: 0.85, y: cy + 0.1, w: cw - 0.5, h: 0.35, fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "head 3.0" });
    bullets(s, [
      "A 25 mm routing envelope per element on top of the 25 mm minimum gap: neighbours 50 mm further apart than sampled",
      `Nothing closer than ${fmt0(D.min_insulation_gap_v3)} mm, while ${fmt0(100 * D.share_measured_below_75)} % of measured gaps are`,
      `The ${fmt0(w1v4)} mm was computed on the sampled gap; physically the files were ${fmt0(w1v3)} mm from the project`,
    ], { x: 0.85, y: cy + 0.5, w: cw - 0.5, h: ch - 0.6 }, 12, "bullets 3.0");
    s.addShape(pres.ShapeType.roundRect, { x: 0.6 + cw + 0.23, y: cy, w: cw, h: ch, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "card 4.0" });
    s.addText("Revision 4.0 — today", { x: 0.85 + cw + 0.23, y: cy + 0.1, w: cw - 0.5, h: 0.35, fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "head 4.0" });
    bullets(s, [
      `The sampled gap is the physical gap; same elements, loads and rows — the spacing moved; ${fmt0(w1v4)} mm holds for geometry you can measure`,
      "All eight files regenerate byte-for-byte on every CI run; every paper number that reproduces is a test",
      "The paper\u2019s composition figures came from an internal build; the public values are restated",
    ], { x: 0.85 + cw + 0.23, y: cy + 0.5, w: cw - 0.5, h: ch - 0.6 }, 12, "bullets 4.0");
    s.addNotes("Rebuilding the release for publication we found the generator added a 25 mm routing envelope on each element ON TOP OF the 25 mm minimum gap: every neighbour sat 50 mm further apart than the sampled gap, and nothing was ever closer than 75 mm - while 42 % of the measured gaps are. The 41 mm in the paper was computed on the sampled gap, not the physical one; measured physically, the paper's files were 89 mm from the project. Revision 4.0 removes the offset. Same elements, same loads, same rows - the spacing moved. The physical gaps are now the sampled ones, and the 41 mm holds for the geometry you can measure in the files. Everything is reproducible: all eight files regenerate byte-for-byte on every CI run; every number in the paper that reproduces is a test, and the ones that do not - the paper's composition figures came from an internal build - are listed with the public values. I would rather tell you this than have you find it. (5:50)");
  }

  // ========================================================================= 9 catalog
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
    s.addText("A two-bin clamp catalog attaches 1 pipe in 9 — and no tray, duct or conduit", { placeholder: "title" });
    s.addChart(pres.ChartType.bar, [{ name: "pipes the catalog can attach (%)", labels: D.tiers, values: D.tiers.map((t) => D.coverage_pct[t]) }], {
      x: 0.6, y: 1.5, w: 7.6, h: 5.1, barDir: "col", barGapWidthPct: 150,
      chartColors: [THEME.colors.accent1],
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", dataLabelFontSize: 10, dataLabelColor: THEME.colors.dk1, dataLabelFontFace: "+mn-lt",
      catAxisLabelColor: INK2, catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", catGridLine: { style: "none" },
      valAxisLabelColor: INK2, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt", valAxisLabelFormatCode: "0",
      valGridLine: { color: GRID, size: 0.75 }, valAxisMinVal: 0, valAxisMaxVal: 25, valAxisMajorUnit: 5,
      showLegend: false, showTitle: true, title: "Share of pipes the catalog can attach, by tier (%)", titleFontSize: 12, titleColor: THEME.colors.dk1, titleFontFace: "+mn-lt",
      objectName: "coverage chart",
    });
    tile(s, 8.5, 1.55, 4.23, 1.55, `${fmt1(D.coverage_overall_pct)} %`, "of the benchmark’s pipes can be attached with the released two bins (48–54 mm at 2.5 kN; 108–114 mm at 4.0 kN)", { labelSize: 11 });
    tile(s, 8.5, 3.3, 4.23, 1.55, `0 of ${D.non_pipe_elements.toLocaleString("en-US")}`, "trays, ducts and conduits: a clamp catalog defines no attachment for them", { labelSize: 11 });
    s.addShape(pres.ShapeType.roundRect, { x: 8.5, y: 5.05, w: 4.23, h: 1.55, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "catalog note card" });
    s.addText([{ text: "Loads never bind; diameter and kind do. ", options: { bold: true } },
      { text: "“Generalise the catalog” becomes a measured requirement: small-bore clamps first, then tray, duct and conduit attachments." }],
      { x: 8.75, y: 5.15, w: 3.75, h: 1.35, fontSize: 12.5, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "catalog note" });
    s.addNotes("Take a released two-bin clamp catalog: 48 to 54 mm at 2.5 kN, 108 to 114 mm at 4.0 kN. Which of the 4,500 benchmark elements can it attach? 11.6 % of pipes; none of the 1,971 trays, ducts and conduits. Loads are never the limit; diameter and kind are. So 'generalise the catalog' is a measurable requirement: small-bore clamps first, then tray, duct and conduit attachments. This is the dataset telling the catalog what it is missing. (7:00)");
  }

  // ========================================================================= 10 limits & ask
  pres.addSection({ title: "Closing" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Closing" });
    s.addText("What it is not, and what we need from you", { placeholder: "title" });
    s.addText("Scope of this revision", { x: 0.6, y: 1.55, w: 7.4, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "scope heading" });
    bullets(s, [
      "One section only: routing, slope, branches and support spacing are outside it (the span is recorded per element, so a method can vary it)",
      "Pipes up to DN100, concrete substrates, no anchor capacity, no duct insulation",
      "Stagger is drawn per element: a bank on one trapeze would be co-planar — next revision, with re-calibration",
      "Row spacing is a fixed 120 mm clear plus stagger, not a trapeze depth",
      "Verified on one residential project: small-bore statistics are checked; congested racks rest on practice and standards",
    ], { x: 0.6, y: 2.1, w: 7.4, h: 2.6 }, 14, "scope bullets");
    s.addText("Next", { x: 0.6, y: 4.75, w: 7.4, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "next heading" });
    bullets(s, [
      "Per-bank stagger (co-planar trapeze banks), re-calibrated against the measured elevation spread",
      "Pipe materials and more substrates from public standards (EN 1057 copper, EN 10312 stainless, EN 1329 plastics)",
      "The same measurement on a commercial corridor model, and an expert plausibility review of generated scenes",
    ], { x: 0.6, y: 5.25, w: 7.4, h: 1.5 }, 14, "next bullets");
    s.addShape(pres.ShapeType.roundRect, { x: 8.4, y: 1.55, w: 4.33, h: 5.05, rectRadius: 0.07, fill: { color: C.background2 }, objectName: "ask card" });
    s.addText("The thing we cannot compute is plausibility", { x: 8.7, y: 1.7, w: 3.75, h: 0.8, fontSize: 17, bold: true, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "ask heading" });
    s.addText("If you coordinate services or design supports: open the gallery, filter for the scenes you know, and tell us what looks wrong. Every rule is one constant and one test away from being changed.",
      { x: 8.7, y: 2.55, w: 3.75, h: 1.55, fontSize: 13, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "ask body" });
    s.addImage({ path: path.join(FIG, "qr_repo.png"), x: 8.7, y: 4.55, w: 1.6, h: 1.6, objectName: "qr" });
    s.addText([{ text: REPO, options: { bold: true, breakLine: true } }, { text: "laviniap@stanford.edu" }],
      { x: 10.45, y: 4.55, w: 2.2, h: 1.6, fontSize: 11, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: "repo link" });
    s.addNotes("One section only: routing, slope, branches, support spacing are outside it - span is recorded per element, so a method can vary it. DN up to 100, concrete substrates, no anchor capacity, no duct insulation. Stagger is drawn per element: a bank on one trapeze would be co-planar - we know, and it is next. Verified on one residential project: small-bore statistics are checked, congested racks rest on practice and standards. The ask: the thing we cannot compute is plausibility. If you coordinate or design supports, open the gallery and tell us what looks wrong. (7:50)");
  }

  // ========================================================================= 11 closing
  {
    const s = addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Closing" });
    s.addText("CrossMEP is the brief, not the answer.", { placeholder: "title" });
    s.addText([
      { text: "7,000 sections  ·  every number traced  ·  verified against a built project  ·  reproducible to the byte  ·  public", options: { breakLine: true } },
      { text: " ", options: { breakLine: true, fontSize: 8 } },
      { text: "Data CC BY 4.0, code MIT.  Not for the structural design of real installations.", options: { fontSize: 13 } },
    ], { placeholder: "body" });
    s.addImage({ path: path.join(FIG, "qr_repo.png"), x: 9.6, y: 2.5, w: 2.3, h: 2.3, objectName: "qr closing" });
    s.addText([{ text: REPO, options: { bold: true, breakLine: true } }, { text: "laviniap@stanford.edu" }],
      { x: 9.3, y: 4.9, w: 3.4, h: 0.8, fontSize: 12, color: C.background1, align: "center", valign: "top", margin: 0, isTextBox: true, objectName: "closing link" });
    s.addNotes("CrossMEP is the brief, not the answer: 7,000 sections, every number traced, verified against a built project, reproducible to the byte, and public. Thank you. (9:00)");
  }

  // ========================================================================= appendix
  pres.addSection({ title: "Appendix" });
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
    s.addText("Appendix A — are the tiers actually ordered?", { placeholder: "title" });
    const img = fitImage(s, path.join(FIG, "03_tiers_stats.png"), { x: 0.6, y: 1.45, w: 12.13, h: 4.75 }, "tier statistics");
    caption(s, "Element count is exact by construction; the medians of clear gap and load are near-monotone (C5/C6 and C7/C8 swap at 125 contexts per tier). Difficulty is carried jointly by count, congestion, load and stacking, with count as the controlled axis.",
      { x: 0.6, y: img.y + img.h + 0.1, w: 12.13, h: 0.5 }, "appendix a caption");
    s.addNotes("Backup: per-tier distributions on the benchmark split.");
  }
  {
    const s = addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
    s.addText("Appendix B — the public files in numbers (benchmark split, revision 4.0)", { placeholder: "title" });
    const hdr = (t) => ({ text: t, options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.dk2 }, fontSize: 12, align: "center" } });
    const num = (t) => ({ text: t, options: { fontSize: 12, color: THEME.colors.dk1, align: "center" } });
    const rows = [[hdr("tier"), hdr("contexts"), hdr("median clear gap (mm)"), hdr("median load (kN)"), hdr("median bundle width (mm)")]];
    for (const t of D.tiers) {
      const m = D.tier_medians[t];
      rows.push([num(t), num("125"), num(m.clear_gap_mm == null ? "—" : fmt0(m.clear_gap_mm)), num(m.load_kN.toFixed(2)), num(fmt0(m.bundle_width_mm))]);
    }
    s.addTable(rows, { x: 0.6, y: 1.55, w: 7.6, colW: [0.9, 1.3, 2.0, 1.6, 1.8], fontFace: THEME.bodyFontFace, fontSize: 12,
      border: { type: "solid", color: GRID, pt: 0.75 }, rowH: 0.42, valign: "middle", margin: 0.05, objectName: "tier table" });
    const k = D.kind_totals;
    tile(s, 8.5, 1.55, 4.23, 1.2, "4,500 elements", `${k.pipe.toLocaleString("en-US")} pipes · ${k.conduit.toLocaleString("en-US")} conduits · ${k.cable_tray} trays · ${k.duct} ducts`, { bigSize: 24, labelSize: 11 });
    tile(s, 8.5, 2.95, 4.23, 1.2, "7,000 contexts", "train 5,000 · val 500 · test 500 · benchmark 1,000 (125 per tier), disjoint seeds", { bigSize: 24, labelSize: 11 });
    tile(s, 8.5, 4.35, 4.23, 1.2, `${fmt1(w1v4)} / ${fmt1(w1bare)} mm`, "Wasserstein-1 to the measured MEP model: insulation surface / bare surface (the measured quantity)", { bigSize: 24, labelSize: 11 });
    s.addText("The paper’s Table 1, Figure 3, Figure 4b and section 5.3 were computed on an internal build with a different pipe library; these are the values of the public files (RESULTS.md in the repository).",
      { x: 0.6, y: 5.6, w: 12.13, h: 0.6, fontSize: 11, color: INK2, valign: "top", margin: 0, isTextBox: true, objectName: "appendix b note" });
    s.addNotes("Backup: the authoritative numbers for the public files.");
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

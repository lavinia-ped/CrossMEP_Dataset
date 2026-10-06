#!/usr/bin/env node
/* Screenshot two Generator Studio sections for the slide deck: the drawing sheet,
   the 3D model and the stored record of each.

       NODE_PATH=$(npm root -g) node scripts/screenshot_contexts.js [studio.html] [out_dir]

   Needs Playwright with a Chromium build.  Defaults: docs/studio/index.html -> docs/figures/
       11_c5_sheet.png, 11_c5_3d.png, 11_c5.json   tier C5, seed 8, section 11 (slide 7: a tray, a duct and pipes on two rows)
       12_c8_sheet.png, 12_c8_3d.png, 12_c8.json   tier C8, seed 1, section 6  (slide 8: three rows, four kinds)
   Offline: STUDIO_ASSETS=<dir> as in screenshot_studio.js.
*/
"use strict";
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const src = path.resolve(process.argv[2] || path.join(ROOT, "docs", "studio", "index.html"));
const outDir = path.resolve(process.argv[3] || path.join(ROOT, "docs", "figures"));
const ASSETS = process.env.STUDIO_ASSETS;
const JOBS = [{ name: "11_c5", tier: "C5", seed: 8, section: 11 }, { name: "12_c8", tier: "C8", seed: 1, section: 6 }];

function fontCss(dir) {
  const faces = [["Barlow Condensed", "barlow-condensed", [500, 600, 700]], ["Barlow", "barlow", [400, 500, 600]], ["IBM Plex Mono", "ibm-plex-mono", [400, 500]]];
  return faces.flatMap(([family, stem, weights]) => weights.map((w) =>
    `@font-face{font-family:"${family}";font-weight:${w};font-style:normal;src:url("file://${path.join(dir, `${stem}-latin-${w}-normal.woff2`)}") format("woff2");}`)).join("\n");
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}), args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  for (const j of JOBS) {
    const page = await browser.newPage({ viewport: { width: 1360, height: 1400 }, deviceScaleFactor: 2, colorScheme: "light" });
    if (ASSETS) {
      await page.route("**/three.min.js", (r) => r.fulfill({ path: path.join(ASSETS, "three.min.js"), contentType: "application/javascript" }));
      await page.route("**/OrbitControls.js", (r) => r.fulfill({ path: path.join(ASSETS, "OrbitControls.js"), contentType: "application/javascript" }));
      await page.route("https://fonts.googleapis.com/**", (r) => r.fulfill({ body: fontCss(ASSETS), contentType: "text/css" }));
    }
    await page.goto("file://" + src, { waitUntil: "load" });
    await page.waitForFunction(() => !document.getElementById("app").hidden);
    await page.evaluate(() => document.fonts.ready);
    await page.click(`[data-tier="${j.tier}"]`);
    for (let i = 0; i < j.seed; i++) await page.click("#seed-inc");
    await page.click(`#grid [data-i="${j.section}"]`);
    await page.click("#enlarge");                       // sheet at full width, the 3D view below it in landscape
    await page.waitForTimeout(1800);
    const rec = await page.evaluate(() => ({ code: document.getElementById("code").textContent, record: JSON.parse(document.getElementById("d-json").textContent) }));
    fs.writeFileSync(path.join(outDir, j.name + ".json"), JSON.stringify(rec, null, 1));
    await (await page.$("#d-sheet")).screenshot({ path: path.join(outDir, j.name + "_sheet.png") });
    await (await page.$("#d-3d")).screenshot({ path: path.join(outDir, j.name + "_3d.png") });
    await page.close();
  }
  await browser.close();
  console.log("wrote", JOBS.map((j) => j.name).join(", "), "to", outDir);
})().catch((e) => { console.error(e); process.exit(1); });

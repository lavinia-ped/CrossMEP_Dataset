#!/usr/bin/env node
/* Screenshot the Generator Studio for the slide deck.

       NODE_PATH=$(npm root -g) node scripts/screenshot_studio.js [studio.html] [out_dir]

   Needs Playwright with a Chromium build (npx playwright install chromium if missing).
   Defaults: docs/studio/index.html -> docs/figures/
       08_studio_demo.png    parameters, drawing sheet and 3D model (tier C7, seed 0, section 1)
       09_studio_wall.png    the drawing sheet of a wall section (tier C6, seed 0, section 5)
       10_studio_mix.png     the drawing sheet of an exact mix (2 pipes, 1 tray, 1 duct, 2 conduits; slab)

   Offline: STUDIO_ASSETS=<dir> serves three.min.js, OrbitControls.js and the
   fontsource woff2 files (barlow-*, barlow-condensed-*, ibm-plex-mono-*) from <dir>
   instead of the CDNs.
*/
"use strict";
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const src = path.resolve(process.argv[2] || path.join(ROOT, "docs", "studio", "index.html"));
const outDir = path.resolve(process.argv[3] || path.join(ROOT, "docs", "figures"));
const ASSETS = process.env.STUDIO_ASSETS;

function fontCss(dir) {
  const faces = [["Barlow Condensed", "barlow-condensed", [500, 600, 700]], ["Barlow", "barlow", [400, 500, 600]], ["IBM Plex Mono", "ibm-plex-mono", [400, 500]]];
  return faces.flatMap(([family, stem, weights]) => weights.map((w) =>
    `@font-face{font-family:"${family}";font-weight:${w};font-style:normal;src:url("file://${path.join(dir, `${stem}-latin-${w}-normal.woff2`)}") format("woff2");}`)).join("\n");
}

async function open(browser, viewport) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: 2, colorScheme: "light" });
  if (ASSETS) {
    await page.route("**/three.min.js", (r) => r.fulfill({ path: path.join(ASSETS, "three.min.js"), contentType: "application/javascript" }));
    await page.route("**/OrbitControls.js", (r) => r.fulfill({ path: path.join(ASSETS, "OrbitControls.js"), contentType: "application/javascript" }));
    await page.route("https://fonts.googleapis.com/**", (r) => r.fulfill({ body: fontCss(ASSETS), contentType: "text/css" }));
  }
  await page.goto("file://" + src, { waitUntil: "load" });
  await page.waitForFunction(() => !document.getElementById("app").hidden);
  await page.evaluate(() => document.fonts.ready);
  return page;
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}), args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });

  // 1. the demo view: parameters bar, drawing sheet and 3D model
  let page = await open(browser, { width: 1360, height: 900 });
  await page.click('[data-tier="C7"]');
  await page.waitForTimeout(1500);
  const box = await page.evaluate(() => {
    const top = document.querySelector(".bar").getBoundingClientRect().top - 12;
    const bottom = document.getElementById("facts").getBoundingClientRect().bottom + 12;
    return { top, bottom };
  });
  await page.screenshot({ path: path.join(outDir, "08_studio_demo.png"), clip: { x: 0, y: box.top, width: 1360, height: box.bottom - box.top } });
  await page.close();

  // 2. two drawing sheets at full width
  const sheet = async (file, act) => {
    const p = await open(browser, { width: 1360, height: 1000 });
    await act(p);
    await p.click("#enlarge");
    await p.waitForTimeout(600);
    await (await p.$("#d-sheet")).screenshot({ path: path.join(outDir, file) });
    await p.close();
  };
  await sheet("09_studio_wall.png", async (p) => { await p.click('[data-tier="C6"]'); await p.click('#grid [data-i="4"]'); });
  await sheet("10_studio_mix.png", async (p) => {
    await p.click("#mode-custom");                                   // starts at 2 pipes + 1 tray
    await p.click('[data-k="ducts"][data-d="1"]');
    await p.click('[data-k="conduits"][data-d="1"]');
    await p.click('[data-k="conduits"][data-d="1"]');
  });
  await browser.close();
  console.log("wrote 08_studio_demo.png, 09_studio_wall.png, 10_studio_mix.png to", outDir);
})().catch((e) => { console.error(e); process.exit(1); });

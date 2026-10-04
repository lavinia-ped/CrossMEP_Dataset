#!/usr/bin/env node
/* Screenshot the interactive gallery for the slide deck.

       NODE_PATH=$(npm root -g) node scripts/screenshot_gallery.js [gallery.html] [out.png]

   Needs Playwright with a Chromium build (npx playwright install chromium if missing).
   Defaults: mep_contexts_gallery.html -> docs/figures/07_gallery_screenshot.png
*/
"use strict";
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const src = path.resolve(process.argv[2] || path.join(ROOT, "mep_contexts_gallery.html"));
const out = path.resolve(process.argv[3] || path.join(ROOT, "docs", "figures", "07_gallery_screenshot.png"));

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 2 });
  await page.goto("file://" + src, { waitUntil: "load" });
  await page.click('button[data-g="tier"][data-v="C6"]');     // show the filter in action
  await page.waitForTimeout(300);
  // crop just below the first row of cards
  const bottom = await page.evaluate(() => {
    const cards = Array.from(document.querySelectorAll("#grid .card")).filter((c) => c.style.display !== "none");
    const top = cards[0].getBoundingClientRect().top;
    const row = cards.filter((c) => Math.abs(c.getBoundingClientRect().top - top) < 2);
    return Math.max(...row.map((c) => c.getBoundingClientRect().bottom)) + 16;
  });
  await page.setViewportSize({ width: 1360, height: Math.ceil(bottom) });
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: 1360, height: Math.ceil(bottom) } });
  await browser.close();
  console.log("wrote", out);
})().catch((e) => { console.error(e); process.exit(1); });

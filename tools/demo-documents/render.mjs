// Renders data/demo/documents/html/*.html as JPEG images next to the manifest (ADR 0007).
// Uses the installed Google Chrome; set CHROMIUM=1 to use Playwright's own Chromium instead.
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const OUT = process.env.OUT_DIR ?? join(ROOT, "data", "demo", "documents");
const HTML = join(OUT, "html");

const files = readdirSync(HTML).filter((f) => f.endsWith(".html")).sort();
const browser = await chromium.launch(process.env.CHROMIUM ? {} : { channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1240, height: 1754 }, deviceScaleFactor: 1 });
for (const name of files) {
  await page.goto(pathToFileURL(join(HTML, name)).href);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: join(OUT, name.replace(/\.html$/, ".jpg")), fullPage: true, type: "jpeg", quality: 85 });
}
await browser.close();
console.log(`${files.length} images written to ${OUT}`);

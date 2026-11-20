// Screenshots of the running system for the report (report/figures/shot-*.png).
//
// Needs the whole system with the demo account (README: docker compose --profile app up),
// Google Chrome, and the demo password in DEMO_PASSWORD. Every shot uses the same window size
// and the synthetic demo data, so the figures can be taken again after the interface changes.
// A shot that fails is reported and skipped; the others are still taken.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const BASE = process.env.BASE_URL ?? "http://localhost:8080";
const EMAIL = process.env.DEMO_EMAIL ?? "demo@visaassist.example";
const PASSWORD = process.env.DEMO_PASSWORD;
const LANG = process.env.SHOT_LANG ?? "en";
const OUT = process.env.OUT_DIR ?? join(dirname(fileURLToPath(import.meta.url)), "..", "figures");
const HEADERS = { "X-Requested-With": "visaassist" };

if (!PASSWORD) {
  console.error("Set DEMO_PASSWORD to the demo account's password.");
  process.exit(1);
}
mkdirSync(OUT, { recursive: true });

const DESKTOP = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 };
const PHONE = {
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
};
const results = [];

async function newContext(browser, options) {
  const context = await browser.newContext({ ...options, locale: LANG === "tr" ? "tr-TR" : "en-GB" });
  await context.addInitScript((lang) => {
    try {
      window.localStorage.setItem("visaassist.language", lang);
    } catch {
      // ignore
    }
  }, LANG);
  return context;
}

async function login(context, email, password) {
  const response = await context.request.post(`${BASE}/api/auth/login`, {
    headers: HEADERS,
    data: { email, password },
  });
  if (!response.ok()) throw new Error(`login failed (${response.status()}) for ${email}`);
}

async function settle(page) {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(900); // entry animations
}

async function open(page, path) {
  await page.goto(`${BASE}${path}`);
  await settle(page);
}

async function shot(name, take) {
  const file = join(OUT, `shot-${name}.png`);
  console.log(`taking shot-${name}.png`);
  try {
    await take(file);
    results.push(`ok      ${file}`);
  } catch (error) {
    results.push(`FAILED  shot-${name}.png: ${error.message.split("\n")[0]}`);
  }
}

/** Hides fixed bars (the phone's bottom navigation) so they do not cover an element. */
async function hideFixed(page) {
  await page.evaluate(() => {
    for (const el of document.querySelectorAll("body *")) {
      if (getComputedStyle(el).position === "fixed") el.style.visibility = "hidden";
    }
  });
}

/** The smallest section (card) around an element, or the element itself. */
function cardOf(locator) {
  return locator.locator("xpath=ancestor::section[1]");
}

const browser = await chromium.launch({ channel: "chrome" });
try {
  // Desktop, demo account
  const desktop = await newContext(browser, DESKTOP);
  await login(desktop, EMAIL, PASSWORD);
  const files = await (await desktop.request.get(`${BASE}/api/applications`)).json();
  const nl = files.find((f) => f.destination === "NL");
  const no = files.find((f) => f.destination === "NO");
  if (!nl || !no) throw new Error("demo files not found: run python -m app.demo.load first");
  const page = await desktop.newPage();

  await shot("checklist", async (file) => {
    await open(page, "/");
    await page.screenshot({ path: file });
  });
  await shot("destinations", async (file) => {
    await open(page, "/destinations");
    await page.screenshot({ path: file });
  });
  await shot("applications", async (file) => {
    await open(page, "/applications");
    await page.screenshot({ path: file });
  });
  await shot("application", async (file) => {
    await open(page, `/applications/${nl.id}`);
    await page.screenshot({ path: file });
  });
  await shot("documents", async (file) => {
    await open(page, `/applications/${nl.id}`);
    await page.getByRole("button", { name: /accommodation|konaklama/i }).first().click();
    await settle(page);
    const heading = page.getByRole("heading", { name: /^(Documents|Belgeler) \(/ }).first();
    await heading.scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -24));
    await page.screenshot({ path: file });
  });
  await shot("rules", async (file) => {
    await open(page, `/applications/${nl.id}`);
    // A clip of the page instead of an element shot: the card holds an endless animation, and an
    // element shot waits for the element to stand still.
    const card = cardOf(page.locator("#rules-heading"));
    await card.scrollIntoViewIfNeeded();
    await settle(page);
    const box = await card.boundingBox();
    if (!box) throw new Error("rules card not visible");
    const scrollY = await page.evaluate(() => window.scrollY); // the box is relative to the viewport
    await page.screenshot({
      path: file,
      fullPage: true,
      clip: { ...box, y: box.y + scrollY },
      animations: "disabled",
    });
  });
  await shot("fields", async (file) => {
    await open(page, `/applications/${nl.id}`);
    await page.getByRole("button", { name: /accommodation|konaklama/i }).first().click();
    await settle(page);
    await page.getByRole("button", { name: /Enter details|Bilgileri gir/ }).first().click();
    await settle(page);
    // The field form is the form that holds the "Enter what the document says" line.
    const form = page.locator("form", { hasText: /Enter what the document says|Belgede yazanlar/i }).first();
    await form.scrollIntoViewIfNeeded();
    await settle(page);
    await form.screenshot({ path: file });
  });
  await shot("findings", async (file) => {
    await open(page, `/applications/${nl.id}/findings`);
    await page.screenshot({ path: file, fullPage: true });
  });
  await shot("norway", async (file) => {
    await open(page, `/applications/${no.id}`);
    await page.screenshot({ path: file });
  });
  await desktop.close();

  // Phone, demo account
  const phone = await newContext(browser, PHONE);
  await login(phone, EMAIL, PASSWORD);
  const mobile = await phone.newPage();
  await shot("mobile-checklist", async (file) => {
    await open(mobile, "/");
    await mobile.screenshot({ path: file });
  });
  await shot("mobile-application", async (file) => {
    await open(mobile, `/applications/${no.id}`);
    await mobile.screenshot({ path: file });
  });
  await shot("mobile-findings", async (file) => {
    await open(mobile, `/applications/${nl.id}/findings`);
    await mobile.screenshot({ path: file });
  });
  await phone.close();

  // Phone, a new account without consent: the consent text before the first upload.
  // The account is synthetic (reserved example domain) and holds no document.
  await shot("mobile-consent", async (file) => {
    const fresh = await newContext(browser, PHONE);
    const email = `screens-${Date.now()}@visaassist.example`;
    const register = await fresh.request.post(`${BASE}/api/auth/register`, {
      headers: HEADERS,
      data: { email, password: `screens-${Math.random().toString(36).slice(2)}-pw` },
    });
    if (!register.ok()) throw new Error(`register failed (${register.status()})`);
    const created = await fresh.request.post(`${BASE}/api/applications`, {
      headers: HEADERS,
      data: {
        destination: "NL",
        profile: "employed",
        trip_start: "2027-04-10",
        trip_end: "2027-04-20",
        application_date: "2027-03-01",
      },
    });
    if (!created.ok()) throw new Error(`creating a file failed (${created.status()})`);
    const { id } = await created.json();
    const p = await fresh.newPage();
    await open(p, `/applications/${id}`);
    await p.getByRole("button", { name: /accommodation|konaklama/i }).first().click();
    await settle(p);
    const consent = p.locator("#consent-heading");
    await consent.scrollIntoViewIfNeeded();
    await settle(p);
    await hideFixed(p);
    await cardOf(consent).screenshot({ path: file });
    await fresh.close();
  });
} finally {
  await browser.close();
  console.log(results.join("\n"));
}

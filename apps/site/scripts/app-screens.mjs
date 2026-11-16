#!/usr/bin/env node
/**
 * Pictures of the real app for the website (apps/site/public/app/*.webp).
 *
 * Logs into a running app with the seeded demo club (synthetic videos, invented players, no real
 * people), opens the key screens and saves them as WebP. Read-only: it opens dialogs but never
 * answers a question, creates a link or changes data. How to run it: apps/site/public/app/README.md.
 *
 *   node apps/site/scripts/app-screens.mjs            # all pictures
 *   node apps/site/scripts/app-screens.mjs ergebnis   # only the named ones
 *
 * Environment: HB_APP_URL (default http://localhost:3000), HB_DEMO_EMAIL, HB_DEMO_PASSWORD,
 * PLAYWRIGHT_CHROMIUM_PATH (optional, a Chromium binary under /opt/pw-browsers).
 * Selectors go by role, visible text and test ids, so small layout changes do not break it.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const OUT = join(here, "..", "public", "app");
const APP = (process.env.HB_APP_URL ?? "http://localhost:3000").replace(/\/$/, "");
const EMAIL = process.env.HB_DEMO_EMAIL ?? "demo@handball-demo.ch";
const PASSWORD = process.env.HB_DEMO_PASSWORD ?? "demo-handball-2026";
const QUALITY = 0.84;

/** Playwright from the site, the repository root or the app's end-to-end tests (@playwright/test). */
async function loadChromium() {
  for (const base of [
    join(here, "package.json"),
    join(here, "..", "..", "..", "package.json"),
    join(here, "..", "..", "web", "package.json"),
  ]) {
    const req = createRequire(base);
    for (const name of ["playwright", "@playwright/test"]) {
      try {
        return req(name).chromium;
      } catch {
        /* next */
      }
    }
  }
  throw new Error(
    "Playwright not found: run pnpm install (apps/web has @playwright/test) or set NODE_PATH.",
  );
}

/** What the website must not show: the Next.js dev badge, blinking carets, running animations. */
const QUIET_CSS = `
  nextjs-portal, [data-nextjs-toast], [data-next-badge-root], #__next-build-watcher { display: none !important; }
  *, *::before, *::after { caret-color: transparent !important; animation-play-state: paused !important; transition: none !important; }
`;

const PHONE = { width: 390, height: 844, scale: 2 };
const DESKTOP = { width: 1280, height: 860, scale: 1 };

/**
 * The pictures. Each opens a screen from the team's start page and returns what to photograph:
 * the viewport (default), one element (`{ element }`) or the top of the page (`{ height }`).
 * `size` is the viewport.
 */
const SHOTS = [
  {
    // taller than the phone: the website lets it scroll slowly from the result to the three things
    name: "ergebnis-phone",
    size: PHONE,
    async open(p) {
      await p.evaluate(() => {
        window.scrollTo(0, 0);
        // the tab bar at the bottom would sit in the middle of a tall picture
        for (const el of document.querySelectorAll("body *")) {
          const cs = getComputedStyle(el);
          if (
            cs.position === "fixed" &&
            cs.bottom === "0px" &&
            el.getBoundingClientRect().height < 140
          )
            el.style.display = "none";
        }
      });
      return { height: 1880 };
    },
  },
  {
    name: "ergebnis",
    size: { ...DESKTOP, height: 1100 },
    async open(p) {
      await p.evaluate(() => window.scrollTo(0, 0));
    },
  },
  {
    name: "hochladen-phone",
    size: PHONE,
    async open(p) {
      // the header's «Video hochladen» opens the same sheet with ?upload=1
      await p.goto(`${p.__team}?upload=1`, { waitUntil: "networkidle" });
      const dialog = p.getByRole("dialog").first();
      await dialog.waitFor({ state: "visible", timeout: 15000 });
      await p.waitForTimeout(600);
      return { element: dialog, pad: 0 };
    },
  },
  {
    name: "video",
    size: { ...DESKTOP, height: 1000 },
    async open(p) {
      await openMatch(p);
      await p.getByRole("tab", { name: "Video", exact: true }).click();
      await p
        .getByTestId("next-scene")
        .or(p.getByRole("button", { name: /Szene merken/ }))
        .first()
        .waitFor({ timeout: 15000 });
      await settle(p);
      await p
        .locator('[role="tablist"]')
        .first()
        .evaluate((el) => {
          const y = el.getBoundingClientRect().top + window.scrollY - 90; // under the sticky header
          window.scrollTo(0, Math.max(0, y));
        });
      await p.waitForTimeout(400);
    },
  },
  {
    name: "pruefen-phone",
    size: PHONE,
    async open(p) {
      await openMatch(p);
      await p.getByTestId("check-link").first().click();
      await p.waitForURL(/\/check/, { timeout: 15000 });
      await p
        .getByRole("heading", { level: 1 })
        .or(p.getByRole("heading", { level: 2 }))
        .first()
        .waitFor({ timeout: 15000 });
      await settle(p);
      // the question and its answers, not only the picture above them
      await p.evaluate(() =>
        window.scrollTo(0, Math.max(0, document.body.scrollHeight - window.innerHeight)),
      );
      await p.waitForTimeout(400);
    },
  },
  {
    name: "szenen",
    size: { ...DESKTOP, height: 940 },
    async open(p) {
      await nav(p, "Szenen");
      await p.getByRole("heading", { level: 1 }).first().waitFor({ timeout: 15000 });
      await settle(p);
    },
  },
  {
    name: "saison",
    size: { ...DESKTOP, height: 820 },
    async open(p) {
      await nav(p, "Saison");
      await p.getByRole("heading", { level: 1 }).first().waitFor({ timeout: 15000 });
      await settle(p);
    },
  },
  {
    name: "teilen-phone",
    size: PHONE,
    async open(p) {
      await p.goto(p.__team.replace(/\/matches$/, "/collections"), { waitUntil: "networkidle" });
      const href = await p
        .locator('a[href*="/collections/"]')
        .evaluateAll((as) =>
          as
            .map((a) => a.getAttribute("href"))
            .find((h) => /\/collections\/[0-9a-f-]{36}$/.test(h ?? "")),
        );
      if (!href) throw new Error("no collection in the demo data");
      await p.goto(APP + href, { waitUntil: "networkidle" });
      await settle(p);
      // «So kommt es im Chat an»: the preview of the link in the team chat, with the share button
      const head = p.getByRole("heading", { name: /im Chat|Chat an|WhatsApp|Teamchat/i }).first();
      if (await head.count()) {
        // the smallest block around the heading that holds the preview card and the button
        await head.evaluate((h) => {
          let el = h;
          while (el.parentElement && el.getBoundingClientRect().height < 320) el = el.parentElement;
          el.setAttribute("data-shot", "");
        });
        const el = p.locator("[data-shot]").first();
        await el.scrollIntoViewIfNeeded();
        await p.waitForTimeout(400);
        return { element: el };
      }
      await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await p.waitForTimeout(400);
    },
  },
];

async function settle(p) {
  await p.waitForLoadState("networkidle").catch(() => {});
  await p.waitForTimeout(900);
}

async function nav(p, name) {
  await p.goto(p.__team, { waitUntil: "networkidle" });
  const link = p.getByRole("link", { name, exact: true }).filter({ visible: true }).first();
  await link.click();
  await p.waitForLoadState("networkidle");
}

async function openMatch(p) {
  await p.goto(p.__team, { waitUntil: "networkidle" });
  await p
    .getByRole("link", { name: /Spiel öffnen/ })
    .first()
    .click();
  await p.waitForURL(/\/matches\/[0-9a-f-]{36}/, { timeout: 15000 });
  await settle(p);
}

async function login(browser) {
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 860 },
    locale: "de-CH",
    timezoneId: "Europe/Zurich",
    reducedMotion: "reduce",
  });
  const p = await ctx.newPage();
  await p.goto(`${APP}/login`, { waitUntil: "networkidle" });
  await p
    .getByLabel(/E-Mail/i)
    .first()
    .fill(EMAIL);
  await p
    .getByLabel(/Passwort/i)
    .first()
    .fill(PASSWORD);
  await p
    .getByRole("button", { name: /^Anmelden$/i })
    .first()
    .click();
  await p.waitForURL(/\/app\/[0-9a-f-]{36}\//, { timeout: 30000 });
  await p.waitForLoadState("networkidle");
  // the team's start page: wherever the login lands, the brand link in the header leads there
  const team = p.url().match(/^(.*\/app\/[0-9a-f-]{36}\/teams\/[0-9a-f-]{36})/)?.[1];
  const state = await ctx.storageState();
  await ctx.close();
  if (!team) throw new Error(`login did not land on a team page: ${p.url()}`);
  return { state, team: `${team}/matches` };
}

/** PNG to WebP in the browser (no image library needed). */
async function toWebp(browser, png) {
  const p = await browser.newPage();
  const data = await p.evaluate(
    async ({ b64, q }) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.naturalWidth;
      c.height = img.naturalHeight;
      c.getContext("2d").drawImage(img, 0, 0);
      return c.toDataURL("image/webp", q).split(",")[1];
    },
    { b64: png.toString("base64"), q: QUALITY },
  );
  await p.close();
  return Buffer.from(data, "base64");
}

async function main() {
  const only = process.argv.slice(2);
  const chromium = await loadChromium();
  const exe = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  mkdirSync(OUT, { recursive: true });
  const { state, team } = await login(browser);
  const failed = [];
  for (const shot of SHOTS.filter((s) => !only.length || only.includes(s.name))) {
    const { width, height, scale } = shot.size;
    const ctx = await browser.newContext({
      storageState: state,
      viewport: { width, height },
      deviceScaleFactor: scale,
      locale: "de-CH",
      timezoneId: "Europe/Zurich",
      reducedMotion: "reduce",
    });
    await ctx.addInitScript((css) => {
      const add = () => {
        const s = document.createElement("style");
        s.textContent = css;
        document.head.appendChild(s);
      };
      if (document.head) add();
      else document.addEventListener("DOMContentLoaded", add);
    }, QUIET_CSS);
    const p = await ctx.newPage();
    p.__team = team;
    try {
      await p.goto(team, { waitUntil: "networkidle" });
      await settle(p);
      const target = await shot.open(p);
      let png;
      if (target?.height) {
        png = await p.screenshot({
          animations: "disabled",
          fullPage: true,
          clip: { x: 0, y: 0, width, height: target.height },
        });
      } else if (target?.element) {
        // the element with a little room around it, inside the page
        const b = await target.element.evaluate((el) => {
          const r = el.getBoundingClientRect();
          return { x: r.x, y: r.y + window.scrollY, width: r.width, height: r.height };
        });
        const pad = target.pad ?? 16;
        const vw = p.viewportSize().width;
        const x = Math.max(0, b.x - pad);
        const clip = {
          x,
          y: Math.max(0, b.y - pad),
          width: Math.min(vw - x, b.width + 2 * pad),
          height: b.height + 2 * pad,
        };
        png = await p.screenshot({ animations: "disabled", clip, fullPage: true });
      } else {
        png = await p.screenshot({ animations: "disabled" });
      }
      const webp = await toWebp(browser, png);
      writeFileSync(join(OUT, `${shot.name}.webp`), webp);
      console.log(`${shot.name}.webp  ${(webp.length / 1024).toFixed(0)} KB`);
    } catch (e) {
      failed.push(shot.name);
      console.error(`${shot.name}: ${e instanceof Error ? e.message.split("\n")[0] : e}`);
    } finally {
      await ctx.close();
    }
  }
  await browser.close();
  if (failed.length) {
    console.error(`not updated: ${failed.join(", ")} (the old pictures stay)`);
    process.exit(1);
  }
}

await main();

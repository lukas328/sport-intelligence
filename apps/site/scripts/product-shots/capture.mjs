#!/usr/bin/env node
/**
 * Step 1 of the product pictures: photographs of the real app (scripts/product-shots/captures).
 *
 * Logs into a running app with the seeded demo club (synthetic videos, invented players, no real
 * people), opens the key screens at twice the pixel density and saves each as WebP, together with
 * where the important things are on it (captures/captures.json: boxes in pixels of the picture,
 * found by role, text and test id). compose.mjs then places them into the designed pictures, so
 * rings and arrows follow the app when its layout changes. Read-only: it opens dialogs but never
 * answers a question, creates a link or changes data. How to run it: README.md next to this file.
 *
 *   node apps/site/scripts/product-shots/capture.mjs            # all screens
 *   node apps/site/scripts/product-shots/capture.mjs video      # only the named ones
 *
 * Environment: HB_APP_URL (default http://localhost:3000), HB_DEMO_EMAIL, HB_DEMO_PASSWORD,
 * HB_API_ORIGIN (only for a second dev server, see below), HB_DEMO_HLS_DIR (see localMedia),
 * PLAYWRIGHT_CHROMIUM_PATH (optional, a Chromium binary under /opt/pw-browsers).
 */
import { existsSync, mkdirSync, readFileSync, statSync, truncateSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadChromium } from "./playwright.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const OUT = join(here, "captures");
const META = join(OUT, "captures.json");
const APP = (process.env.HB_APP_URL ?? "http://localhost:3000").replace(/\/$/, "");
/**
 * Only for a second dev server on another port: the API takes writes (the login, a search) only
 * from the origin it knows, so requests to /v1 then say they come from there.
 */
const API_ORIGIN = process.env.HB_API_ORIGIN?.replace(/\/$/, "");
const EMAIL = process.env.HB_DEMO_EMAIL ?? "demo@handball-demo.ch";
const PASSWORD = process.env.HB_DEMO_PASSWORD ?? "demo-handball-2026";
/** sources for the composition, so a little better than what the website gets */
const QUALITY = 0.9;

/** What the pictures must not show: the Next.js dev badge, blinking carets, running animations. */
const QUIET_CSS = `
  nextjs-portal, [data-nextjs-toast], [data-next-badge-root], #__next-build-watcher { display: none !important; }
  *, *::before, *::after { caret-color: transparent !important; animation-play-state: paused !important; transition: none !important; }
`;

/**
 * Helpers inside the app's page, used by the `find` functions below. Everything goes by visible
 * text, role or test id; a box is { x, y, width, height } in CSS pixels of the viewport.
 */
function pageHelpers() {
  const leaves = (root = document.body) => Array.from(root.querySelectorAll("*"));
  const hb = {
    /** the innermost element whose text is exactly `t` (or matches a RegExp) */
    text(t, root) {
      const ok = (s) => (t instanceof RegExp ? t.test(s) : s === t);
      const all = leaves(root).filter((e) => ok((e.textContent ?? "").trim()));
      return (
        all.find((e) => !Array.from(e.children).some((c) => ok((c.textContent ?? "").trim()))) ??
        null
      );
    },
    /** the closest ancestor (or the element) for which test(el) holds */
    up(el, test) {
      for (let e = el; e; e = e.parentElement) if (test(e)) return e;
      return null;
    },
    /** the smallest element that contains all the texts */
    around(...texts) {
      let best = null;
      for (const e of leaves()) {
        const s = e.textContent ?? "";
        if (!texts.every((t) => s.includes(t))) continue;
        if (!best || best.contains(e)) best = e;
      }
      return best;
    },
    /** one box around several elements or boxes */
    union(items) {
      const rs = Array.from(items)
        .map((i) => (i instanceof Element ? i.getBoundingClientRect() : i))
        .filter((r) => r && r.width > 0 && r.height > 0);
      if (!rs.length) return null;
      const x = Math.min(...rs.map((r) => r.x));
      const y = Math.min(...rs.map((r) => r.y));
      return {
        x,
        y,
        width: Math.max(...rs.map((r) => r.x + r.width)) - x,
        height: Math.max(...rs.map((r) => r.y + r.height)) - y,
      };
    },
    /** hides the tab bar at the bottom of the phone (it would sit in the middle of a picture) */
    hideTabBar() {
      for (const el of document.querySelectorAll("body *")) {
        const cs = getComputedStyle(el);
        if (
          cs.position === "fixed" &&
          cs.bottom === "0px" &&
          el.getBoundingClientRect().height < 140
        )
          el.style.display = "none";
      }
    },
    /**
     * hides (keeps its room) the block around a text, e.g. an empty «Notizen»; a RegExp hides
     * only the text that matches it, e.g. the clock of a video the picture covers
     */
    hide(text) {
      const el = hb.text(text);
      if (!el) return 0;
      if (text instanceof RegExp) {
        el.style.visibility = "hidden";
        return 1;
      }
      let b = el;
      while (b.parentElement && b.parentElement.getBoundingClientRect().height < 260) b = b.parentElement;
      b.style.visibility = "hidden";
      return 1;
    },
    /** the shot dots of the half court in the block that holds `label` */
    dots(label) {
      const el = hb.text(label);
      const box = el && hb.up(el, (e) => e.querySelector("svg circle"));
      return box ? hb.union(box.querySelectorAll("svg circle")) : null;
    },
  };
  window.__hb = hb;

  // A note for this one account that a visitor would not see in their own club: the request to
  // confirm the demo e-mail address. Hidden whenever it shows up, never answered.
  const tidy = () => {
    if (!document.body) return;
    const t = hb.text(/^Bestätige deine E-Mail/);
    if (!t) return;
    let el = t;
    while (el.parentElement && el.parentElement.getBoundingClientRect().height < 160)
      el = el.parentElement;
    el.style.display = "none";
  };
  setInterval(tidy, 150);
}

const PHONE = { width: 390, height: 844, scale: 2 };
const DESKTOP = { width: 1280, height: 860, scale: 2 };
/**
 * The steps (U1, U3): one moment of the app cut out large, so its words read at 390 px. A narrow
 * phone (360), so the cut-out holds fewer, bigger letters; three times the density for the 2x file.
 */
const PHONE_STEP = { width: 360, height: 780, scale: 3 };

/**
 * The screens. `open` brings the page into place; `find` names the boxes compose.mjs needs (each
 * runs in the page, `hb` are the helpers above). A box that cannot be found is left out; the
 * templates then fall back to a sensible spot and compose.mjs says so. `clip` photographs the
 * top of the page instead of the viewport.
 */
const SHOTS = [
  {
    // the laptop in the hero: result, course of the match and the three things with their shots
    name: "ergebnis-laptop",
    // a little taller than 16:10, so the shots of the first thing are fully on the screen
    size: { width: 1440, height: 940, scale: 2 },
    async open(p) {
      await p.evaluate(() => window.scrollTo(0, 0));
    },
    find: {
      dots: (hb) => hb.dots("Gegentore über aussen rechts"),
      things: (hb) =>
        hb.union([hb.text("1 von 3"), hb.text("Gegentore über aussen rechts")].filter(Boolean)),
    },
  },
  {
    // the phone in the hero, taller than the screen: the site lets it run slowly down and back
    name: "ergebnis-phone-tall",
    size: PHONE,
    clip: 1880,
    async open(p) {
      await p.evaluate(() => {
        window.scrollTo(0, 0);
        window.__hb.hideTabBar();
      });
    },
    find: {},
  },
  {
    name: "video",
    size: { ...DESKTOP, height: 1000 },
    // a clean state: no empty «Noch keine Notiz» under the three things. The picture of the
    // synthetic clip is covered by the hall recording (stage.js), so its own clock goes with it
    hide: ["Noch keine Notiz zu dieser Phase.", /^\d+:\d\d \/ \d+:\d\d$/],
    async open(p) {
      await openMatch(p);
      // the second goal over the right wing (the 6th minute of the website's match), opened as
      // «Szene zeigen» opens it (?tab=video&scene=): a phase early in the match with its goals
      const scene = await p.evaluate(async () => {
        const [, org, match] = location.pathname.match(/\/app\/([^/]+)\/matches\/([^/?]+)/) ?? [];
        const r = await fetch(`/v1/orgs/${org}/matches/${match}/graphics`, { credentials: "include" });
        const goals = ((await r.json()).goals ?? [])
          .filter((g) => g.team === "opp" && g.zone === "ra" && g.t_ms != null)
          .sort((a, b) => a.minute - b.minute);
        return goals[1]?.event_id ?? null;
      });
      if (!scene) throw new Error("no second goal over the right wing");
      const url = new URL(p.url());
      url.search = `?tab=video&scene=${scene}`;
      await p.goto(url.toString(), { waitUntil: "load", timeout: 90000 });
      await p
        .getByTestId("next-scene")
        .or(p.getByRole("button", { name: /Szene merken/ }))
        .first()
        .waitFor({ timeout: 15000 });
      await settle(p);
      // the player stands where the app puts it, at the start of that scene; the hall recording
      // covers the clip's picture and draws the line of a 60-minute video there (templates: `at`)
      await p.waitForTimeout(1200);
      await p
        .locator('[role="tablist"]')
        .first()
        .evaluate((el) => {
          const y = el.getBoundingClientRect().top + window.scrollY - 90; // under the sticky header
          window.scrollTo(0, Math.max(0, y));
        });
      // photographed while it plays: paused, the video shows a big play button over the players
      await p.waitForTimeout(500);
    },
    find: {
      video: () => document.querySelector("video"),
      active: (hb) => {
        const t = hb.text(/läuft gerade/);
        return (
          t && hb.up(t, (e) => e.tagName === "BUTTON" || e.tagName === "A" || e.tagName === "LI")
        );
      },
      list: (hb) => {
        const t = hb.text(/läuft gerade/);
        return t && hb.up(t, (e) => e.tagName === "UL" || e.tagName === "OL");
      },
      // the marks of all goals with the labels under them
      timeline: (hb) => {
        const labels = hb.around("Anwurf", "Halbzeit", "Schluss");
        return (
          labels &&
          hb.up(labels, (e) => e.querySelector("svg") && e.getBoundingClientRect().height > 60)
        );
      },
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
    find: {
      search: (hb) => {
        const field = Array.from(
          document.querySelectorAll("input, textarea, [role=searchbox], [role=combobox]"),
        ).find((i) => i.getBoundingClientRect().width > 300);
        // the box around the field (with its magnifier), not only the text input
        return field ? hb.up(field, (e) => e.getBoundingClientRect().height >= 44) : null;
      },
      answer: (hb) => {
        const t = hb.text(/^von \d+ Gegentoren/) ?? hb.text(/von \d+ Gegentoren/);
        return t && hb.up(t, (e) => e.getBoundingClientRect().height > 60);
      },
      play: () =>
        Array.from(document.querySelectorAll("button, a")).find((b) =>
          /abspielen/.test(b.textContent),
        ) ?? null,
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
    find: {
      // the bars of the first theme: one per match
      bars: (hb) => {
        const title = hb.text("Gegentore über aussen rechts");
        const row =
          title &&
          hb.up(
            title,
            (e) =>
              /Rotdorn|Wirbelstern|Nachtwind/.test(e.textContent) && e.getBoundingClientRect().height > 60,
          );
        if (!row) return null;
        const names = Array.from(row.querySelectorAll("*")).filter(
          (e) => e.children.length === 0 && /^(Rotdorn|Wirbelstern|Nachtwind)/.test(e.textContent.trim()),
        );
        const chart =
          names.length &&
          hb.up(
            names[0],
            (e) => names.every((n) => e.contains(n)) && e.getBoundingClientRect().height > 40,
          );
        return chart || null;
      },
      dots: (hb) => hb.dots("Aussen rechts"),
      court: (hb) => {
        const t = hb.text("Aussen rechts");
        const box = t && hb.up(t, (e) => e.querySelector("svg circle"));
        const svg =
          box &&
          Array.from(box.querySelectorAll("svg")).sort(
            (a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width,
          )[0];
        return svg ?? null;
      },
    },
  },
  {
    // step 2 (U1): «Zu welchem Spiel gehört das Video?» with the matches, large
    name: "step-hochladen",
    size: PHONE_STEP,
    async open(p) {
      await p.goto(`${p.__team}?upload=1`, { waitUntil: "networkidle" });
      await p.getByRole("dialog").first().waitFor({ state: "visible", timeout: 15000 });
      await p.waitForTimeout(700);
    },
    find: {
      dialog: () => document.querySelector('[role="dialog"]'),
      title: (hb) => hb.text("Video hochladen", document.querySelector('[role="dialog"]')),
      question: (hb) => hb.text(/Zu welchem Spiel/, document.querySelector('[role="dialog"]')),
      first: (hb) => hb.text("SG Blitzfang", document.querySelector('[role="dialog"]'))?.closest("button, a, label, li") ?? null,
      second: (hb) => hb.text("TV Silberpfeil", document.querySelector('[role="dialog"]'))?.closest("button, a, label, li") ?? null,
    },
  },
  {
    // step 2 (U1): the same match while its video goes up, the bar and «… % hochgeladen». This
    // one writes: it starts a real upload of an empty file the size of a match video into the
    // first match and holds it there, so run it only on a stack of your own (capture.mjs runs it
    // only when named) and seed again afterwards
    name: "step-hochladen-laeuft",
    size: PHONE_STEP,
    writes: true,
    async open(p) {
      await p.goto(`${p.__team}?upload=1`, { waitUntil: "networkidle" });
      const dialog = p.getByRole("dialog").first();
      await dialog.waitFor({ state: "visible", timeout: 15000 });
      await dialog.getByText("SG Blitzfang").first().click();
      const input = p.getByTestId("video-file").first();
      await input.waitFor({ state: "attached", timeout: 30000 });
      // the parts go up until about an eighth of the file is there, then the rest waits: the
      // picture shows a running upload without filling the stack's storage
      const file = matchFile();
      const partSize = 5 * 1024 * 1024;
      const stopAt = Math.ceil((FILE_SIZE * 0.12) / partSize);
      let parts = 0;
      await p.route(
        (url) => /[?&]partNumber=/.test(url.search),
        (route) => {
          if (route.request().method() !== "PUT") return route.continue();
          parts += 1;
          return parts <= stopAt ? route.continue() : new Promise(() => {});
        },
      );
      await input.setInputFiles(file);
      const anyway = p.getByRole("button", { name: "Jetzt hochladen" });
      if (await anyway.isVisible({ timeout: 3000 }).catch(() => false)) await anyway.click();
      const progress = p.getByTestId("upload-progress");
      await progress.waitFor({ timeout: 30000 });
      await p.waitForFunction(
        (want) => {
          const m = document.querySelector('[data-testid="upload-progress"]')?.textContent?.match(/(\d+)\s*%/);
          return m && Number(m[1]) >= want;
        },
        11,
        { timeout: 120000 },
      );
      await p.waitForTimeout(1500);
      await p.getByTestId("upload-running").evaluate((el) => {
        window.__hb.hideTabBar();
        el.scrollIntoView({ block: "center" });
      });
      await p.waitForTimeout(400);
    },
    find: {
      running: () => document.querySelector('[data-testid="upload-running"]'),
      progress: () => document.querySelector('[data-testid="upload-progress"]'),
      heading: () => document.querySelector("h1"),
    },
  },
  {
    // step 3 (U1): «Passt das Spielfeld?» with the picture and its yellow field, large
    name: "step-pruefen",
    // taller than a phone, so the picture and the answers are on one capture
    size: { ...PHONE_STEP, height: 960 },
    async open(p) {
      await openMatch(p);
      const check = await p.getByTestId("check-link").first().getAttribute("href");
      if (!check) throw new Error("no link «Prüfen»");
      await p.goto(new URL(check, APP).toString(), { waitUntil: "networkidle" });
      await p.getByRole("heading", { level: 1 }).or(p.getByRole("heading", { level: 2 })).first().waitFor({ timeout: 15000 });
      await settle(p);
      await p.evaluate(() => {
        window.__hb.hideTabBar();
        const pic = window.__hb.text(/^Zieh die vier gelben Punkte/)?.closest("section, div");
        const top = pic ? pic.getBoundingClientRect().top + window.scrollY - 330 : 0;
        window.scrollTo(0, Math.max(0, top));
      });
      await p.waitForTimeout(400);
    },
    find: {
      // the picture the question is about (the frame of the video with the proposed field)
      picture: () => {
        const imgs = Array.from(document.querySelectorAll("img, canvas, video, svg")).filter((e) => e.getBoundingClientRect().width > 250);
        return imgs.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0] ?? null;
      },
      hint: (hb) => hb.text(/^Zieh die vier gelben Punkte/),
      count: (hb) => hb.text(/^Frage \d+ von \d+$/),
      question: () => document.querySelector("h1") ?? document.querySelector("h2"),
      yes: () => Array.from(document.querySelectorAll("button")).find((b) => b.textContent.trim() === "Passt") ?? null,
      no: () => Array.from(document.querySelectorAll("button")).find((b) => b.textContent.trim() === "Weiss nicht") ?? null,
    },
  },
  {
    // step 4 (U3): the first of the three things with its shots on the court, large
    name: "step-dinge",
    size: PHONE_STEP,
    async open(p) {
      await openMatch(p);
      await p.evaluate(() => {
        const t = window.__hb.text("1 von 3") ?? window.__hb.text(/^1\s*von\s*3$/);
        // under the sticky head, with room above the number
        if (t) window.scrollTo(0, t.getBoundingClientRect().top + window.scrollY - 96);
        window.__hb.hideTabBar();
      });
      await p.waitForTimeout(500);
    },
    find: {
      kicker: (hb) => hb.text("1 von 3") ?? hb.text(/^1\s*von\s*3$/),
      title: () => Array.from(document.querySelectorAll("h2, h3")).find((h) => /^Gegentore\s+über\s+aussen\s+rechts$/.test(h.textContent.trim())),
      dots: (hb) => {
        const t = Array.from(document.querySelectorAll("h2, h3")).find((h) => /^Gegentore\s+über\s+aussen\s+rechts$/.test(h.textContent.trim()));
        const box = t && hb.up(t, (e) => e.querySelector("svg circle"));
        return box ? hb.union(box.querySelectorAll("svg circle")) : null;
      },
      court: (hb) => {
        const t = Array.from(document.querySelectorAll("h2, h3")).find((h) => /^Gegentore\s+über\s+aussen\s+rechts$/.test(h.textContent.trim()));
        const box = t && hb.up(t, (e) => e.querySelector("svg circle"));
        const svg = box && Array.from(box.querySelectorAll("svg")).sort((a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width)[0];
        return svg ?? null;
      },
      scenes: () => Array.from(document.querySelectorAll("button, a")).find((b) => /^\d+ Szenen$/.test(b.textContent.trim())) ?? null,
    },
  },
  {
    // the app picture of the start page as a phone shows it (U22): the video, under it the
    // scenes of the phase, the one playing in yellow
    name: "video-phone",
    // tall enough for the video and the list under it on one capture
    size: { ...PHONE_STEP, height: 1500 },
    hide: [/^\d+:\d\d \/ \d+:\d\d$/],
    async open(p) {
      await openMatch(p);
      const scene = await p.evaluate(async () => {
        const [, org, match] = location.pathname.match(/\/app\/([^/]+)\/matches\/([^/?]+)/) ?? [];
        const r = await fetch(`/v1/orgs/${org}/matches/${match}/graphics`, { credentials: "include" });
        const goals = ((await r.json()).goals ?? []).filter((g) => g.team === "opp" && g.zone === "ra" && g.t_ms != null).sort((a, b) => a.minute - b.minute);
        return goals[1]?.event_id ?? null;
      });
      if (!scene) throw new Error("no second goal over the right wing");
      const url = new URL(p.url());
      url.search = `?tab=video&scene=${scene}`;
      await p.goto(url.toString(), { waitUntil: "load", timeout: 90000 });
      await p.getByTestId("next-scene").or(p.getByRole("button", { name: /Szene merken/ })).first().waitFor({ timeout: 15000 });
      await settle(p);
      await p.waitForTimeout(1200);
      await p.evaluate(() => {
        window.__hb.hideTabBar();
        const v = document.querySelector("video");
        if (v) window.scrollTo(0, Math.max(0, v.getBoundingClientRect().top + window.scrollY - 64));
      });
      await p.waitForTimeout(500);
    },
    find: {
      video: () => document.querySelector("video"),
      active: (hb) => {
        const t = hb.text(/läuft gerade/);
        return t && hb.up(t, (e) => e.tagName === "BUTTON" || e.tagName === "A" || e.tagName === "LI");
      },
      list: (hb) => {
        const t = hb.text(/läuft gerade/);
        return t && hb.up(t, (e) => e.tagName === "UL" || e.tagName === "OL");
      },
      phase: (hb) => hb.text(/^Minute \d+ bis \d+$/),
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
      // «So kommt es im Chat an» near the top of the screen, the share button below it
      const head = p.getByRole("heading", { name: /im Chat|Chat an|WhatsApp|Teamchat/i }).first();
      await head.waitFor({ timeout: 15000 });
      // the heading low enough that the share button is on the screen too (without the tab bar)
      await head.evaluate((h) => {
        window.__hb.hideTabBar();
        const y = h.getBoundingClientRect().top + window.scrollY - 255;
        window.scrollTo(0, Math.max(0, y));
      });
      await p.waitForTimeout(500);
    },
    find: {
      card: (hb) => {
        const h = hb.text(/im Chat|Chat an|Teamchat/);
        const sec =
          h &&
          hb.up(
            h,
            (e) =>
              e.querySelector("img, svg, [style*=background]") &&
              e.getBoundingClientRect().height > 200,
          );
        if (!sec) return null;
        // the preview: the biggest box after the heading that is not the whole section
        const kids = Array.from(sec.querySelectorAll("*")).filter((e) => {
          const r = e.getBoundingClientRect();
          return (
            r.top > h.getBoundingClientRect().bottom &&
            r.height > 120 &&
            r.height < 400 &&
            r.width > 200
          );
        });
        return kids[0] ?? null;
      },
      share: () =>
        Array.from(document.querySelectorAll("button, a")).find((b) =>
          /^Link teilen$/.test(b.textContent.trim()),
        ) ?? null,
    },
  },
];

/** The match file of step-hochladen-laeuft: empty (sparse), the size of a phone's match video. */
const FILE_SIZE = Math.round(3.4 * 1024 ** 3);
function matchFile() {
  const dir = join(tmpdir(), "hb-product-shots");
  mkdirSync(dir, { recursive: true });
  const file = join(dir, "Spiel.mp4");
  if (!existsSync(file) || statSync(file).size !== FILE_SIZE) {
    writeFileSync(file, "");
    truncateSync(file, FILE_SIZE);
  }
  return file;
}

/** See API_ORIGIN. */
async function sameOrigin(ctx) {
  if (!API_ORIGIN) return;
  await ctx.route(`${APP}/v1/**`, async (route) => {
    const headers = {
      ...(await route.request().allHeaders()),
      origin: API_ORIGIN,
      referer: `${API_ORIGIN}/`,
    };
    await route.continue({ headers });
  });
}

/**
 * Optional: the video's player media from a folder instead of the running app (HB_DEMO_HLS_DIR,
 * laid out like the video's media folder: hls/master.m3u8, hls/720p/index.m3u8, init.mp4,
 * seg_*.m4s). For a stack seeded before the demo footage changed: render the match with the
 * current `handball_vision.synthetic --demo` (same seed and length as scripts/seed.py) and package
 * it, so the pictures show the footage a fresh seed gives. Files not in the folder come from the app.
 */
async function localMedia(ctx) {
  const dir = process.env.HB_DEMO_HLS_DIR;
  if (!dir) return;
  await ctx.route(/\/media\/[^?]+\.(m3u8|m4s|mp4)(\?|$)/, async (route) => {
    const path = new URL(route.request().url()).pathname.split("/media/")[1] ?? "";
    const file = join(dir, path);
    if (path.includes("..") || !existsSync(file)) return route.continue();
    const type = path.endsWith(".m3u8") ? "application/vnd.apple.mpegurl" : "video/mp4";
    await route.fulfill({ status: 200, contentType: type, body: readFileSync(file) });
  });
}

async function settle(p) {
  await p.waitForLoadState("networkidle").catch(() => {});
  await p.waitForTimeout(900);
}

async function nav(p, name) {
  await p.goto(p.__team, { waitUntil: "networkidle" });
  // follow the link's address instead of clicking: a client-side change has no load to wait for
  const link = p.getByRole("link", { name, exact: true }).filter({ visible: true }).first();
  const href = await link.getAttribute("href");
  if (!href) throw new Error(`no link «${name}»`);
  await p.goto(new URL(href, APP).toString(), { waitUntil: "networkidle" });
}

async function openMatch(p) {
  await p.goto(p.__team, { waitUntil: "networkidle" });
  const href = await p
    .getByRole("link", { name: /Spiel öffnen/ })
    .first()
    .getAttribute("href");
  if (!href) throw new Error("no link «Spiel öffnen»");
  // "load", not "networkidle": a player that keeps fetching its video never lets the network rest
  await p.goto(new URL(href, APP).toString(), { waitUntil: "load", timeout: 90000 });
  await settle(p);
}

async function login(browser) {
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 860 },
    locale: "de-CH",
    timezoneId: "Europe/Zurich",
    reducedMotion: "reduce",
  });
  await sameOrigin(ctx);
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
  const team = p.url().match(/\/app\/[0-9a-f-]{36}\/teams\/[0-9a-f-]{36}/)?.[0];
  const state = await ctx.storageState();
  await ctx.close();
  if (!team) throw new Error(`login did not land on a team page: ${p.url()}`);
  return { state, team: `${APP}${team}/matches` };
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
      return { b64: c.toDataURL("image/webp", q).split(",")[1], width: c.width, height: c.height };
    },
    { b64: png.toString("base64"), q: QUALITY },
  );
  await p.close();
  return { buf: Buffer.from(data.b64, "base64"), width: data.width, height: data.height };
}

async function main() {
  const only = process.argv.slice(2);
  const chromium = await loadChromium();
  const exe = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  mkdirSync(OUT, { recursive: true });
  const meta = existsSync(META) ? JSON.parse(readFileSync(META, "utf8")) : {};
  const { state, team } = await login(browser);
  const failed = [];
  // a screen that writes into the account runs only when named (see step-hochladen-laeuft)
  for (const shot of SHOTS.filter((s) => (only.length ? only.includes(s.name) : !s.writes))) {
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
    await ctx.addInitScript(pageHelpers);
    await sameOrigin(ctx);
    await localMedia(ctx);
    const p = await ctx.newPage();
    p.__team = team;
    try {
      await p.goto(team, { waitUntil: "networkidle" });
      await settle(p);
      await shot.open(p);
      // what the app shows stays as it is: the seed tells the website's story (scripts/seed.py)
      for (const text of shot.hide ?? []) {
        const what = text instanceof RegExp ? { re: text.source } : { s: text };
        const ok = await p.evaluate(
          (w) => window.__hb.hide(w.re ? new RegExp(w.re) : w.s),
          what,
        );
        if (!ok) console.warn(`${shot.name}: nothing to hide for «${text}»`);
      }
      const rects = {};
      const missing = [];
      for (const [key, fn] of Object.entries(shot.find)) {
        const r = await p
          .evaluate((src) => {
            const res = new Function("hb", `return (${src})(hb)`)(window.__hb);
            const box = res instanceof Element ? res.getBoundingClientRect() : res;
            return box && box.width > 0
              ? { x: box.x, y: box.y, width: box.width, height: box.height }
              : null;
          }, fn.toString())
          .catch(() => null);
        if (r) rects[key] = [r.x, r.y, r.width, r.height].map((v) => Math.round(v * scale));
        else missing.push(key);
      }
      const png = shot.clip
        ? await p.screenshot({
            animations: "disabled",
            fullPage: true,
            clip: { x: 0, y: 0, width, height: shot.clip },
          })
        : await p.screenshot({ animations: "disabled" });
      const webp = await toWebp(browser, png);
      writeFileSync(join(OUT, `${shot.name}.webp`), webp.buf);
      meta[shot.name] = { width: webp.width, height: webp.height, scale, rects };
      console.log(
        `${shot.name}.webp  ${webp.width} x ${webp.height}  ${(webp.buf.length / 1024).toFixed(0)} KB` +
          (missing.length ? `  (not found: ${missing.join(", ")})` : ""),
      );
    } catch (e) {
      failed.push(shot.name);
      console.error(`${shot.name}: ${e instanceof Error ? e.message.split("\n")[0] : e}`);
    } finally {
      await ctx.close();
    }
  }
  await browser.close();
  const sorted = Object.fromEntries(Object.entries(meta).sort(([a], [b]) => a.localeCompare(b)));
  // boxes on one line each, as prettier writes them
  const json = JSON.stringify(sorted, null, 2).replace(
    /\[\s+([-\d.,\s]+?)\s+\]/g,
    (_, inner) => `[${inner.split(/,\s*/).join(", ")}]`,
  );
  writeFileSync(META, `${json}\n`);
  if (failed.length) {
    console.error(`not updated: ${failed.join(", ")} (the old captures stay)`);
    process.exit(1);
  }
}

await main();

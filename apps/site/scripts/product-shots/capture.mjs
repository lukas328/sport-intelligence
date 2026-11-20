#!/usr/bin/env node
/**
 * Step 1 of the product pictures: photographs of the real app (scripts/product-shots/captures).
 *
 * Logs into a running app with the seeded demo club (synthetic videos, invented players, no real
 * people), opens the key screens at two or three times the pixel density and saves each as WebP,
 * together with where the important things are on it (captures/captures.json: boxes in pixels of
 * the picture, found by role, text and test id). compose.mjs then places them into the designed
 * pictures, so rings and arrows follow the app when its layout changes. Read-only: it opens
 * dialogs but never answers a question, creates a link or changes data. The one exception is
 * `--colours`: it sets the demo club's colour before each round and back to green at the end
 * (U45). How to run it: README.md next to this file.
 *
 *   node apps/site/scripts/product-shots/capture.mjs            # all screens
 *   node apps/site/scripts/product-shots/capture.mjs video      # only the named ones
 *   node apps/site/scripts/product-shots/capture.mjs --colours  # the app pictures' screens in
 *        each club colour of colours.mjs (or --colours=red,blue), into captures/colours/<colour>/
 *
 * Environment: HB_APP_URL (default http://localhost:3000), HB_DEMO_EMAIL, HB_DEMO_PASSWORD,
 * HB_API_ORIGIN (only for a second dev server, see below), HB_DEMO_HLS_DIR (see localMedia),
 * PLAYWRIGHT_CHROMIUM_PATH (optional, a Chromium binary under /opt/pw-browsers).
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { COLOURS, DEMO_COLOUR, LANGS, NAMES, captureDir } from "./variants.mjs";
import { loadChromium } from "./playwright.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const OUT = join(here, "captures");
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
 * The app's words the screens are found by, in each language (the app's message catalogues,
 * apps/web/messages: anlauf.throwOff, scenesPage.playAll …). `hb.w(key)` gives
 * the one of the page's language; a RegExp also matches a part.
 */
const WORDS = {
  de: {
    throwOff: "Anwurf",
    halfTime: "Halbzeit",
    fullTime: "Schluss",
    noNotes: "Noch keine Notiz zu dieser Phase.",
    keepScene: /Szene merken/,
    openMatch: /Spiel öffnen/,
    scenes: "Szenen",
    season: "Saison",
    answer: /von \d+ Gegentoren/,
    playAll: /^Alle \d+ abspielen$/,
    wingTheme: /^Gegentore\s+über\s+aussen\s+rechts$/,
    wingZone: "Aussen rechts",
    firstOf3: /^1\s*von\s*3$/,
    nScenes: /^\d+ Szenen$/,
    phase: /^Minute \d+ bis \d+$/,
    inChat: /im Chat|Chat an|Teamchat/,
    shareLink: /^Link teilen$/,
    confirmMail: /^Bestätige deine E-Mail/,
  },
  fr: {
    throwOff: "Engagement",
    halfTime: "Mi-temps",
    fullTime: "Fin",
    noNotes: "Pas encore de note sur cette phase.",
    keepScene: /Garder la scène/,
    openMatch: /Ouvrir le match/,
    scenes: "Scènes",
    season: "Saison",
    answer: /sur \d+ buts encaissés/,
    playAll: /^Lire les \d+$/,
    wingTheme: /^Buts\s+encaissés\s+par\s+l.ailier\s+droit$/,
    wingZone: "Aile droite",
    firstOf3: /^1\s*sur\s*3$/,
    nScenes: /^\d+ scènes$/,
    phase: /^Minute \d+ à \d+$/,
    inChat: /dans le chat/,
    shareLink: /^Partager le lien$/,
    confirmMail: /^Confirme ton adresse e-mail/,
  },
  en: {
    throwOff: "Throw-off",
    halfTime: "Half time",
    fullTime: "Full time",
    noNotes: "No note on this phase yet.",
    keepScene: /Keep scene/,
    openMatch: /Open match/,
    scenes: "Scenes",
    season: "Season",
    answer: /of \d+ goals conceded/,
    playAll: /^Play all \d+$/,
    wingTheme: /^Goals\s+conceded\s+down\s+the\s+right\s+wing$/,
    wingZone: "Right wing",
    firstOf3: /^1\s*of\s*3$/,
    nScenes: /^\d+ scenes$/,
    phase: /^Minute \d+ to \d+$/,
    inChat: /in the chat/,
    shareLink: /^Share link$/,
    confirmMail: /^Confirm your e-mail/,
  },
};

/** the words of a language as they go into the page (RegExps as their source) */
const pageWords = (lang) =>
  Object.fromEntries(
    Object.entries(WORDS[lang]).map(([k, v]) => [k, v instanceof RegExp ? { re: v.source } : v]),
  );

/**
 * Helpers inside the app's page, used by the `find` functions below. Everything goes by visible
 * text, role or test id; a box is { x, y, width, height } in CSS pixels of the viewport.
 */
function pageHelpers(words) {
  const leaves = (root = document.body) => Array.from(root.querySelectorAll("*"));
  const hb = {
    /** a word of WORDS in the page's language */
    w(key) {
      const v = words[key];
      if (v === undefined) throw new Error(`no word «${key}»`);
      return typeof v === "string" ? v : new RegExp(v.re);
    },
    /** the innermost element whose text is exactly `t` (or matches a RegExp) */
    text(t, root) {
      const ok = (s) => (t instanceof RegExp ? t.test(s) : s === t);
      const all = leaves(root).filter((e) => ok((e.textContent ?? "").trim()));
      return (
        all.find((e) => !Array.from(e.children).some((c) => ok((c.textContent ?? "").trim()))) ??
        null
      );
    },
    /** the scene that plays in the list beside the video: pressed, with background and bar (the
     * words «läuft gerade» left the list with UX-04, 19.11.) */
    playing() {
      return document.querySelector('li > button[aria-pressed="true"]');
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
    const t = hb.text(hb.w("confirmMail"));
    if (!t) return;
    let el = t;
    while (el.parentElement && el.parentElement.getBoundingClientRect().height < 160)
      el = el.parentElement;
    el.style.display = "none";
  };
  setInterval(tidy, 150);
}

const PHONE = { width: 390, height: 844, scale: 2 };
/**
 * The screens of the large pictures at three times the density: the website shows them up to
 * 1550 px wide and makes 3x files of them (BEFUNDE-4 U44), so the app's words stay sharp there.
 */
const DESKTOP = { width: 1280, height: 860, scale: 3 };
/**
 * The cut-outs (app-result, video-phone): one moment of the app large, so its words read at
 * 390 px. A narrow phone (360), so the cut-out holds fewer, bigger letters; three times the
 * density for the 2x file.
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
    app: true,
    size: { ...DESKTOP, height: 1100 },
    // a clean state: no empty «Noch keine Notiz» under the three things. The picture of the
    // synthetic clip is covered by the hall recording (stage.js), so its own clock goes with it
    hide: (w) => [w.noNotes, /^\d+:\d\d \/ \d+:\d\d$/],
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
        .or(p.getByRole("button", { name: p.__w.keepScene }))
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
        const t = hb.playing();
        return (
          t && hb.up(t, (e) => e.tagName === "BUTTON" || e.tagName === "A" || e.tagName === "LI")
        );
      },
      list: (hb) => {
        const t = hb.playing();
        return t && hb.up(t, (e) => e.tagName === "UL" || e.tagName === "OL");
      },
      // the marks of all goals with the labels under them
      timeline: (hb) => {
        const labels = hb.around(hb.w("throwOff"), hb.w("halfTime"), hb.w("fullTime"));
        return (
          labels &&
          hb.up(labels, (e) => e.querySelector("svg") && e.getBoundingClientRect().height > 60)
        );
      },
    },
  },
  {
    name: "szenen",
    app: true,
    size: { ...DESKTOP, height: 940 },
    async open(p) {
      await nav(p, p.__w.scenes);
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
        const t = hb.text(hb.w("answer"));
        return t && hb.up(t, (e) => e.getBoundingClientRect().height > 60);
      },
      play: (hb) =>
        Array.from(document.querySelectorAll("button, a")).find((b) =>
          hb.w("playAll").test(b.textContent.trim()),
        ) ?? null,
    },
  },
  {
    name: "saison",
    app: true,
    size: { ...DESKTOP, height: 820 },
    async open(p) {
      await nav(p, p.__w.season);
      await p.getByRole("heading", { level: 1 }).first().waitFor({ timeout: 15000 });
      await settle(p);
    },
    find: {
      // the bars of the first theme: one per match
      bars: (hb) => {
        const title = hb.text(hb.w("wingTheme"));
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
      dots: (hb) => hb.dots(hb.w("wingZone")),
      court: (hb) => {
        const t = hb.text(hb.w("wingZone"));
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
    // the first of the three things with its shots on the court, large («Über uns», app-result)
    name: "step-dinge",
    app: true,
    size: PHONE_STEP,
    async open(p) {
      await openMatch(p);
      await p.evaluate(() => {
        const t = window.__hb.text(window.__hb.w("firstOf3"));
        // under the sticky head, with room above the number
        if (t) window.scrollTo(0, t.getBoundingClientRect().top + window.scrollY - 96);
        window.__hb.hideTabBar();
      });
      await p.waitForTimeout(500);
    },
    find: {
      kicker: (hb) => hb.text(hb.w("firstOf3")),
      title: (hb) => Array.from(document.querySelectorAll("h2, h3")).find((h) => hb.w("wingTheme").test(h.textContent.trim())),
      dots: (hb) => {
        const t = Array.from(document.querySelectorAll("h2, h3")).find((h) => hb.w("wingTheme").test(h.textContent.trim()));
        const box = t && hb.up(t, (e) => e.querySelector("svg circle"));
        return box ? hb.union(box.querySelectorAll("svg circle")) : null;
      },
      court: (hb) => {
        const t = Array.from(document.querySelectorAll("h2, h3")).find((h) => hb.w("wingTheme").test(h.textContent.trim()));
        const box = t && hb.up(t, (e) => e.querySelector("svg circle"));
        const svg = box && Array.from(box.querySelectorAll("svg")).sort((a, b) => b.getBoundingClientRect().width - a.getBoundingClientRect().width)[0];
        return svg ?? null;
      },
      scenes: (hb) => Array.from(document.querySelectorAll("button, a")).find((b) => hb.w("nScenes").test(b.textContent.trim())) ?? null,
    },
  },
  {
    // the app picture of the start page as a phone shows it (U22): the video, under it the
    // scenes of the phase, the one playing in yellow
    name: "video-phone",
    app: true,
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
      await p.getByTestId("next-scene").or(p.getByRole("button", { name: p.__w.keepScene })).first().waitFor({ timeout: 15000 });
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
        const t = hb.playing();
        return t && hb.up(t, (e) => e.tagName === "BUTTON" || e.tagName === "A" || e.tagName === "LI");
      },
      list: (hb) => {
        const t = hb.playing();
        return t && hb.up(t, (e) => e.tagName === "UL" || e.tagName === "OL");
      },
      phase: (hb) => hb.text(hb.w("phase")),
    },
  },
  {
    name: "teilen-phone",
    // the picture «share» goes up to 3x too (U44)
    size: { ...PHONE, scale: 3 },
    app: true,
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
      const head = p.getByRole("heading", { name: p.__w.inChat }).first();
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
        const h = hb.text(hb.w("inChat"));
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
      share: (hb) =>
        Array.from(document.querySelectorAll("button, a")).find((b) =>
          hb.w("shareLink").test(b.textContent.trim()),
        ) ?? null,
    },
  },
];

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
    .getByRole("link", { name: p.__w.openMatch })
    .first()
    .getAttribute("href");
  if (!href) throw new Error(`no link «${p.__w.openMatch.source}»`);
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



/**
 * Writes into the demo account through the app's own API, from a page of the team (the session's
 * cookie and its CSRF token): `run(call, ids)` gets `call(method, path, body)` under /v1/orgs/<org>.
 */
async function withApi(browser, state, team, run, arg) {
  const ctx = await browser.newContext({ storageState: state });
  await sameOrigin(ctx);
  const p = await ctx.newPage();
  try {
    await p.goto(team, { waitUntil: "load" });
    return await p.evaluate(
      async ({ src, arg }) => {
        const csrf = document.cookie.match(/(?:^|; )hb_csrf=([^;]+)/)?.[1];
        const headers = {
          "content-type": "application/json",
          ...(csrf ? { "x-csrf-token": decodeURIComponent(csrf) } : {}),
        };
        const [, org, teamId] = location.pathname.match(/\/app\/([^/]+)\/teams\/([^/]+)/) ?? [];
        const call = async (method, path, body) => {
          const r = await fetch(`/v1/orgs/${org}${path}`, {
            method,
            credentials: "include",
            headers,
            body: body && JSON.stringify(body),
          });
          if (!r.ok) throw new Error(`${method} ${path}: ${r.status}`);
          return r.status === 204 ? null : r.json();
        };
        return new Function("call", "teamId", "arg", `return (${src})(call, teamId, arg)`)(
          call,
          teamId,
          arg,
        );
      },
      { src: run.toString(), arg },
    );
  } finally {
    await ctx.close();
  }
}

/**
 * The demo club in another colour (U45), as a coach would set it in the club settings: the club's
 * two colours, and the shirt of each of its matches that wears the club's colour (a match with a
 * video keeps its shirt when the club colour changes, so it is set too).
 */
async function setClubColour(browser, state, team, [first, second]) {
  const known = [DEMO_COLOUR[0], ...Object.values(COLOURS).map(([c]) => c)];
  const n = await withApi(
    browser,
    state,
    team,
    async (call, teamId, { first, second, known }) => {
      await call("PATCH", "", { primary_color: first, secondary_color: second });
      let n = 0;
      for (const m of await call("GET", `/teams/${teamId}/matches`)) {
        const match = await call("GET", `/matches/${m.id}`);
        const own = (match.kit_own ?? "").toLowerCase();
        if (match.kind === "scouting" || !known.includes(own) || own === first) continue;
        await call("PATCH", `/matches/${m.id}`, { kit_own: first });
        n++;
      }
      return n;
    },
    { first, second, known },
  );
  console.log(`club colour ${first} (shirts of ${n} matches)`);
}

/**
 * The demo data's names in a language (NAMES): the team and the collection of the website's
 * Tuesday, as a coach of that language names them. Everything else stays as it is.
 */
async function setNames(browser, state, team, lang) {
  const all = Object.values(NAMES);
  await withApi(
    browser,
    state,
    team,
    async (call, teamId, { to, all }) => {
      await call("PATCH", `/teams/${teamId}`, { name: to.team });
      for (const c of await call("GET", `/teams/${teamId}/collections`))
        if (all.some((n) => n.collection === c.title) && c.title !== to.collection)
          await call("PATCH", `/collections/${c.id}`, { title: to.collection });
    },
    { to: NAMES[lang], all },
  );
  console.log(`names in ${lang}: ${NAMES[lang].team}, ${NAMES[lang].collection}`);
}

/** Photographs `shots` in `lang` into `dir` (its captures.json keeps the other screens' entries). */
async function captureAll(browser, state, team, shots, dir, lang) {
  mkdirSync(dir, { recursive: true });
  const metaFile = join(dir, "captures.json");
  const meta = existsSync(metaFile) ? JSON.parse(readFileSync(metaFile, "utf8")) : {};
  const failed = [];
  for (const shot of shots) {
    const { width, height, scale } = shot.size;
    const ctx = await browser.newContext({
      storageState: state,
      viewport: { width, height },
      deviceScaleFactor: scale,
      locale: LANGS[lang],
      timezoneId: "Europe/Zurich",
      reducedMotion: "reduce",
    });
    // the app's language: its own setting (the cookie its language switch sets)
    await ctx.addCookies([{ name: "NEXT_LOCALE", value: LANGS[lang], url: APP }]);
    await ctx.addInitScript((css) => {
      const add = () => {
        const s = document.createElement("style");
        s.textContent = css;
        document.head.appendChild(s);
      };
      if (document.head) add();
      else document.addEventListener("DOMContentLoaded", add);
    }, QUIET_CSS);
    await ctx.addInitScript(pageHelpers, pageWords(lang));
    await sameOrigin(ctx);
    await localMedia(ctx);
    const p = await ctx.newPage();
    p.__team = team;
    p.__w = WORDS[lang];
    try {
      await p.goto(team, { waitUntil: "networkidle" });
      await settle(p);
      await shot.open(p);
      // what the app shows stays as it is: the seed tells the website's story (scripts/seed.py)
      const hide = typeof shot.hide === "function" ? shot.hide(WORDS[lang]) : (shot.hide ?? []);
      for (const text of hide) {
        const what = text instanceof RegExp ? { re: text.source } : { s: text };
        const ok = await p.evaluate(
          (w) => window.__hb.hide(w.re ? new RegExp(w.re) : w.s),
          what,
        );
        if (!ok) console.warn(`${shot.name} (${lang}): nothing to hide for «${text}»`);
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
      writeFileSync(join(dir, `${shot.name}.webp`), webp.buf);
      meta[shot.name] = { width: webp.width, height: webp.height, scale, rects };
      console.log(
        `${dir.slice(OUT.length + 1) || "."}/${shot.name}.webp  ${webp.width} x ${webp.height}  ${(webp.buf.length / 1024).toFixed(0)} KB` +
          (missing.length ? `  (not found: ${missing.join(", ")})` : ""),
      );
    } catch (e) {
      failed.push(shot.name);
      console.error(`${shot.name} (${lang}): ${e instanceof Error ? e.message.split("\n")[0] : e}`);
    } finally {
      await ctx.close();
    }
  }
  const sorted = Object.fromEntries(Object.entries(meta).sort(([a], [b]) => a.localeCompare(b)));
  // boxes on one line each, as prettier writes them
  const json = JSON.stringify(sorted, null, 2).replace(
    /\[\s+([-\d.,\s]+?)\s+\]/g,
    (_, inner) => `[${inner.split(/,\s*/).join(", ")}]`,
  );
  writeFileSync(metaFile, `${json}\n`);
  return failed;
}

/** `--name=a,b` as a list, `--name` as all of `all`, missing as `fallback` */
function listArg(args, name, all, fallback) {
  const flag = args.find((a) => a === `--${name}` || a.startsWith(`--${name}=`));
  if (!flag) return fallback;
  const list = flag.includes("=") ? flag.split("=")[1].split(",") : all;
  for (const v of list) if (!all.includes(v)) throw new Error(`unknown ${name} «${v}»`);
  return list;
}

async function main() {
  const args = process.argv.slice(2);
  const only = args.filter((a) => !a.startsWith("--"));
  // the app pictures' screens in each language (default all; --langs=fr) and, with --colours
  // (all of variants.mjs, or --colours=red,blue), once per club colour (U45)
  const langs = listArg(args, "langs", Object.keys(LANGS), Object.keys(LANGS));
  const colours = listArg(args, "colours", Object.keys(COLOURS), null);
  const chromium = await loadChromium();
  const exe = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  const { state, team } = await login(browser);
  const failed = [];
  // a screen that writes into the account (`writes: true`, none today) runs only when named
  const named = SHOTS.filter((s) => (only.length ? only.includes(s.name) : !s.writes));
  try {
    for (const colour of colours ?? [null]) {
      if (colour) await setClubColour(browser, state, team, COLOURS[colour]);
      for (const lang of langs) {
        // the other languages and the colours only for the app pictures' screens
        const shots = named.filter((s) => s.app || (lang === "de" && !colour));
        if (!shots.length) continue;
        if (lang !== "de") await setNames(browser, state, team, lang);
        const dir = captureDir(OUT, lang, colour);
        const missed = await captureAll(browser, state, team, shots, dir, lang);
        failed.push(...missed.map((n) => `${n} (${[lang, colour].filter(Boolean).join(", ")})`));
        if (lang !== "de") await setNames(browser, state, team, "de");
      }
    }
  } finally {
    // the demo club as scripts/seed.py makes it: its green and the German names
    if (colours) await setClubColour(browser, state, team, DEMO_COLOUR);
    if (langs.some((l) => l !== "de")) await setNames(browser, state, team, "de");
  }
  await browser.close();
  if (failed.length) {
    console.error(`not updated: ${failed.join(", ")} (the old captures stay)`);
    process.exit(1);
  }
}

await main();

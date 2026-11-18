#!/usr/bin/env node
/**
 * Step 2 of the product pictures: places the app captures (captures/, made by capture.mjs) into
 * the designed pictures (templates/*.html with stage.css and stage.js) and writes them as WebP
 * to public/product/: <name>.webp (1x), <name>-2x.webp and, for a picture the page shows large,
 * <name>-3x.webp (the template's `densities`). The 2x and 3x files are photographed at their own
 * density, so the words stay sharp; each file is written at the best quality under its budget,
 * but never under MIN_QUALITY (BEFUNDE-4 U44: lower qualities left visible artefacts).
 * The manifest src/lib/product-shots.json holds the sizes, densities, club colours and callouts
 * (arrow and label positions in per cent); the website draws the arrows and writes the labels as
 * real text in the visitor's language (src/components/product-shot.tsx, texts in
 * src/messages/*.ts, `product`).
 *
 *   node apps/site/scripts/product-shots/compose.mjs             # all pictures
 *   node apps/site/scripts/product-shots/compose.mjs app-result  # only the named ones
 *   node apps/site/scripts/product-shots/compose.mjs --preview /tmp/shots   # plus PNGs with arrows
 *   node apps/site/scripts/product-shots/compose.mjs --no-colours           # only the green files
 *
 * A template with words in the picture names its languages (`S.stage(…, { langs })`);
 * it is then made once per language: <name>-de.webp, <name>-fr.webp, <name>-en.webp.
 *
 * A picture made of captures shows the app, and the app speaks the visitor's language: it is made
 * once per language of variants.mjs from the captures in that language (captures/ for German,
 * captures/fr/, captures/en/), <name>-<lang>.webp. A template with `colours: true` is also made
 * in each club colour (U45), <name>-<lang>-<colour>.webp at `colourDensities` (default 1x and 2x),
 * from the captures capture.mjs took with the demo club in that colour
 * (captures/colours/<colour>/<lang>/, kept out of the repository for its size); its Keil takes
 * the colour too. Without those captures the colour files stay as they are, and compose.mjs says so.
 *
 * Needs no app and no network: only Chromium (Playwright) and the captures.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { COLOURS, LANGS, captureDir } from "./variants.mjs";
import { loadChromium } from "./playwright.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const TEMPLATES = join(here, "templates");
const CAPTURES = join(here, "captures");
const OUT = join(here, "..", "..", "public", "product");
const MANIFEST = join(here, "..", "..", "src", "lib", "product-shots.json");
/**
 * What one file may weigh, by density. The quality goes down in steps until it fits, but never
 * under MIN_QUALITY: a file that does not fit there stays heavier, and compose.mjs says so. The
 * pictures load lazily, so a 2x or 3x file may weigh a few hundred KB; the 1x stays small.
 */
const BUDGET = { 1: 110 * 1024, 2: 300 * 1024, 3: 560 * 1024 };
const MIN_QUALITY = 0.82;
const QUALITIES = [0.9, 0.88, 0.86, 0.84, MIN_QUALITY];
/** the files of a picture unless its template asks for more (`S.stage(…, { densities })`) */
const DENSITIES = [1, 2];

const args = process.argv.slice(2);
const previewAt = args.indexOf("--preview");
const PREVIEW = previewAt >= 0 ? args[previewAt + 1] : null;
const NO_COLOURS = args.includes("--no-colours");
const only = args.filter((a, i) => !a.startsWith("--") && (previewAt < 0 || i !== previewAt + 1));

/** the captures of one folder (captures/ or captures/colours/<colour>/), each with its file */
function readCaptures(dir) {
  const file = join(dir, "captures.json");
  if (!existsSync(file)) return {};
  const meta = JSON.parse(readFileSync(file, "utf8"));
  for (const [name, c] of Object.entries(meta)) {
    const img = join(dir, `${name}.webp`);
    if (existsSync(img)) c.src = pathToFileURL(img).href;
    else delete meta[name];
  }
  return meta;
}

/** one file of a picture: <base>.webp, <base>-2x.webp, <base>-3x.webp */
const fileOf = (base, d) => (d === 1 ? `${base}.webp` : `${base}-${d}x.webp`);

/**
 * PNG to WebP in the browser, scaled to `width`, at the best quality that fits `budget` bytes,
 * never under MIN_QUALITY (`over`: it did not fit even there).
 */
async function encode(page, png, width, budget) {
  return page.evaluate(
    async ({ b64, width, budget, qualities }) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = width;
      c.height = Math.round((img.naturalHeight * width) / img.naturalWidth);
      const g = c.getContext("2d");
      g.imageSmoothingQuality = "high";
      g.drawImage(img, 0, 0, c.width, c.height);
      let out = null;
      for (const q of qualities) {
        const b = c.toDataURL("image/webp", q).split(",")[1];
        out = { b64: b, q, width: c.width, height: c.height, over: (b.length * 3) / 4 > budget };
        if (!out.over) break;
      }
      return out;
    },
    { b64: png.toString("base64"), width, budget, qualities: QUALITIES },
  );
}

/** For --preview: the arrows and a box per label drawn over the picture, as the website does. */
function previewOverlay(shot) {
  const svg = shot.callouts
    .map(({ from, to, bend }) => {
      const [ax, ay] = from;
      const [tx, ty] = to;
      const mx = (ax + tx) / 2 - (ty - ay) * bend;
      const my = (ay + ty) / 2 + (tx - ax) * bend;
      return `<path d="M${ax} ${ay}Q${mx} ${my} ${tx} ${ty}" fill="none" stroke="#16171a" stroke-width="2.5"/><circle cx="${tx}" cy="${ty}" r="4" fill="#16171a"/>`;
    })
    .join("");
  const labels = shot.callouts
    .map(({ id, from, place }) => {
      const t = {
        r: "translate(4px,-50%)",
        l: "translate(calc(-100% - 4px),-50%)",
        t: "translate(-50%,calc(-100% - 4px))",
        b: "translate(-50%,4px)",
        tl: "translate(-14px,calc(-100% - 4px))",
        tr: "translate(calc(-100% + 14px),calc(-100% - 4px))",
        bl: "translate(-14px,4px)",
        br: "translate(calc(-100% + 14px),4px)",
      }[place];
      return `<b style="position:absolute;left:${from[0]}px;top:${from[1]}px;transform:${t};background:#ffd23c;font:700 15px sans-serif;padding:4px 8px;box-shadow:3px 3px 0 #16171a;white-space:nowrap">${id} (Beispieltext)</b>`;
    })
    .join("");
  return `<svg style="position:absolute;inset:0" width="${shot.width}" height="${shot.height}">${svg}</svg>${labels}`;
}

/** the callouts, the marks and the lettering of a shot in per cent of the picture, as the manifest holds them */
function placed(shot) {
  const pct = ([x, y]) => [
    +((x / shot.width) * 100).toFixed(2),
    +((y / shot.height) * 100).toFixed(2),
  ];
  return {
    callouts: shot.callouts.map((c) => ({
      id: c.id,
      from: pct(c.from),
      to: pct(c.to),
      place: c.place,
      bend: c.bend,
      ...(c.max ? { max: c.max } : {}),
    })),
    ...(shot.marks
      ? {
          marks: Object.fromEntries(
            Object.entries(shot.marks).map(([id, [x, y, w, h]]) => [id, [...pct([x, y]), ...pct([w, h])]]),
          ),
        }
      : {}),
    ...(shot.lettering
      ? {
          lettering: [
            ...pct([shot.lettering[0], shot.lettering[1]]),
            ...pct([shot.lettering[2], shot.lettering[3]]),
          ],
        }
      : {}),
  };
}

async function main() {
  const capsOf = (lang, colour) => readCaptures(captureDir(CAPTURES, lang, colour));
  const chromium = await loadChromium();
  const exe = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  mkdirSync(OUT, { recursive: true });
  if (PREVIEW) mkdirSync(PREVIEW, { recursive: true });
  const manifest = existsSync(MANIFEST) ? JSON.parse(readFileSync(MANIFEST, "utf8")) : {};
  const names = readdirSync(TEMPLATES)
    .filter((f) => f.endsWith(".html"))
    .map((f) => basename(f, ".html"))
    .filter((n) => !only.length || only.includes(n));
  const encoder = await browser.newPage();
  let failed = 0;

  /**
   * the template in `lang` with the captures `caps` (and the Keil in `club`), at `scale`: its
   * shot and the stage
   */
  async function open(name, lang, caps, scale, club) {
    const ctx = await browser.newContext({
      viewport: { width: 1600, height: 1200 },
      deviceScaleFactor: scale,
    });
    await ctx.addInitScript(
      ({ m, club }) => {
        window.CAPTURES = m;
        window.CLUB = club;
      },
      { m: caps, club },
    );
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const url = pathToFileURL(join(TEMPLATES, `${name}.html`));
    if (lang) url.search = `?lang=${lang}`;
    await page.goto(url.href);
    await page
      .waitForFunction(() => window.READY || window.SHOT?.error, null, { timeout: 20000 })
      .catch(() => {});
    const shot = errors.length ? null : await page.evaluate(() => window.READY);
    if (!shot) {
      await ctx.close();
      throw new Error(errors.join("; ") || "the template did not finish (no done())");
    }
    return { ctx, page, shot, stage: page.locator("#stage") };
  }

  /** what a template is: its languages (words in the picture), the captures it uses, its options */
  async function probe(name) {
    const { ctx, shot } = await open(name, null, capsOf("de", null), 1);
    await ctx.close();
    return shot;
  }

  /**
   * One picture: the template in `lang`, made of the captures `caps`, photographed at each of
   * `densities` and written to <base>.webp, <base>-2x.webp … Returns the shot.
   */
  async function render(name, lang, base, caps, densities, club) {
    let first = null;
    try {
      first = await open(name, lang, caps, 2, club);
      const { shot, stage, page } = first;
      // a colour's files may weigh less (`colourBudget2x`): there are seven of them per language
      const budget = (d) => (club && shot[`colourBudget${d}x`]) || shot[`budget${d}x`] || BUDGET[d];
      const shoot = (s) =>
        s.screenshot({ omitBackground: shot.transparent, animations: "disabled" });
      const two = await shoot(stage);
      const files = [];
      for (const d of densities) {
        let png = two;
        if (d > 2) {
          // photographed at its own density: the frame's words and the app's are drawn, not blown up
          const big = await open(name, lang, caps, d, club);
          png = await shoot(big.stage);
          await big.ctx.close();
        }
        const out = await encode(encoder, png, shot.width * d, budget(d));
        writeFileSync(join(OUT, fileOf(base, d)), Buffer.from(out.b64, "base64"));
        const kb = ((out.b64.length * 3) / 4 / 1024).toFixed(0);
        files.push(`${d}x ${kb} KB (q ${out.q}${out.over ? ", over budget" : ""})`);
        if (d === 1) files.unshift(`${out.width} x ${out.height}`);
      }
      console.log(`${base}  ${files.join("  ")}`);
      for (const w of shot.warnings) console.warn(`  ! ${w}`);
      if (PREVIEW && !club) {
        await page.evaluate(
          (html) => document.getElementById("stage").insertAdjacentHTML("beforeend", html),
          previewOverlay(shot),
        );
        await stage.screenshot({ path: join(PREVIEW, `${base}.png`), omitBackground: false });
      }
      return shot;
    } catch (e) {
      failed++;
      console.error(`${base}: ${e instanceof Error ? e.message.split("\n")[0] : e}`);
      return null;
    } finally {
      await first?.ctx.close();
    }
  }

  /** the manifest's entry of a picture */
  function enter(base, shot, densities, extra = {}) {
    manifest[base] = {
      width: shot.width,
      height: shot.height,
      densities,
      ...extra,
      ...placed(shot),
    };
  }

  for (const name of names) {
    let shot;
    try {
      shot = await probe(name);
    } catch (e) {
      failed++;
      console.error(`${name}: ${e instanceof Error ? e.message.split("\n")[0] : e}`);
      continue;
    }
    const densities = shot.densities ?? DENSITIES;
    if (!shot.uses.length) {
      // a drawn picture: once, or once per language of its words (the steps)
      for (const lang of shot.langs ?? [null]) {
        const base = [name, lang].filter(Boolean).join("-");
        const made = await render(name, lang, base, {}, densities, null);
        if (made) enter(base, made, densities);
      }
      continue;
    }
    // a picture of the app: once per language, from the captures in that language
    for (const old of [1, 2, 3].map((d) => join(OUT, fileOf(name, d))))
      if (existsSync(old)) rmSync(old); // from before the languages
    delete manifest[name];
    for (const lang of Object.keys(LANGS)) {
      const base = `${name}-${lang}`;
      const caps = capsOf(lang, null);
      const lacking = shot.uses.filter((u) => !caps[u]);
      if (lacking.length) {
        failed++;
        console.error(`${base}: no captures in ${lang} (${lacking.join(", ")}): run capture.mjs`);
        continue;
      }
      const made = await render(name, lang, base, caps, densities, null);
      if (!made) continue;
      // and in each club colour where the template asks for it (U45), from the captures with
      // the demo club in that colour; without them the colour's files stay as they are
      const cd = shot.colourDensities ?? DENSITIES;
      const colours = [];
      for (const colour of shot.colours ? Object.keys(COLOURS) : []) {
        const cbase = `${base}-${colour}`;
        const ccaps = { ...caps, ...capsOf(lang, colour) };
        const ready = shot.uses.every((u) => ccaps[u] && ccaps[u].src !== caps[u].src);
        if (ready && !NO_COLOURS) {
          const c = await render(name, lang, cbase, ccaps, cd, COLOURS[colour][0]);
          if (!c) continue;
          colours.push(colour);
          // the colour changes the paint, not the layout: the page draws the green one's callouts
          if (JSON.stringify(placed(c).callouts) !== JSON.stringify(placed(made).callouts))
            console.warn(`  ! ${cbase}: the callouts differ from the green picture`);
        } else if (cd.every((d) => existsSync(join(OUT, fileOf(cbase, d))))) {
          colours.push(colour);
          if (!NO_COLOURS) console.warn(`  ! ${cbase}: no captures in this colour, the files stay`);
        }
      }
      enter(base, made, densities, colours.length ? { colours, colourDensities: cd } : {});
    }
  }
  await browser.close();
  const sorted = Object.fromEntries(
    Object.entries(manifest).sort(([a], [b]) => a.localeCompare(b)),
  );
  // short lists on one line, as prettier writes them
  const json = JSON.stringify(sorted, null, 2)
    .replace(/\[\s+([-\d.,\s]+?)\s+\]/g, (_, inner) => `[${inner.split(/,\s*/).join(", ")}]`)
    .replace(/\[\s+((?:"[a-z]+",?\s*)+?)\s+\]/g, (_, inner) => `[${inner.split(/,\s*/).join(", ")}]`);
  writeFileSync(MANIFEST, `${json}\n`);
  if (failed) process.exit(1);
}

await main();

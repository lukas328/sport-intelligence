#!/usr/bin/env node
/**
 * Step 2 of the product pictures: places the app captures (captures/, made by capture.mjs) into
 * the designed pictures (templates/*.html with stage.css and stage.js) and writes them as WebP
 * to public/product/: <name>.webp (1x) and <name>-2x.webp, each as small as the budget allows.
 * The manifest src/lib/product-shots.json holds the sizes and the callouts (arrow and label
 * positions in per cent); the website draws the arrows and writes the labels as real text in the
 * visitor's language (src/components/product-shot.tsx, texts in src/messages/*.ts, `product`).
 *
 *   node apps/site/scripts/product-shots/compose.mjs             # all pictures
 *   node apps/site/scripts/product-shots/compose.mjs step-check  # only the named ones
 *   node apps/site/scripts/product-shots/compose.mjs --preview /tmp/shots   # plus PNGs with arrows
 *
 * Needs no app and no network: only Chromium (Playwright) and the committed captures.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { loadChromium } from "./playwright.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const TEMPLATES = join(here, "templates");
const CAPTURES = join(here, "captures");
const OUT = join(here, "..", "..", "public", "product");
const MANIFEST = join(here, "..", "..", "src", "lib", "product-shots.json");
/** what one picture may weigh; the quality goes down in steps until it fits */
const BUDGET = { "1x": 100 * 1024, "2x": 150 * 1024 };
const QUALITIES = [0.9, 0.86, 0.82, 0.78, 0.74, 0.7, 0.66, 0.62];

const args = process.argv.slice(2);
const previewAt = args.indexOf("--preview");
const PREVIEW = previewAt >= 0 ? args[previewAt + 1] : null;
const only = args.filter((a, i) => a !== "--preview" && (previewAt < 0 || i !== previewAt + 1));

function captures() {
  const meta = JSON.parse(readFileSync(join(CAPTURES, "captures.json"), "utf8"));
  for (const [name, c] of Object.entries(meta))
    c.src = pathToFileURL(join(CAPTURES, `${name}.webp`)).href;
  return meta;
}

/** PNG to WebP in the browser, scaled to `width`, at the best quality that fits `budget` bytes. */
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
        out = { b64: b, q, width: c.width, height: c.height };
        if ((b.length * 3) / 4 <= budget) break;
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

async function main() {
  const meta = captures();
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
  for (const name of names) {
    const ctx = await browser.newContext({
      viewport: { width: 1600, height: 1200 },
      deviceScaleFactor: 2,
    });
    await ctx.addInitScript((m) => {
      window.CAPTURES = m;
    }, meta);
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    try {
      await page.goto(pathToFileURL(join(TEMPLATES, `${name}.html`)).href);
      await page
        .waitForFunction(() => window.READY || window.SHOT?.error, null, { timeout: 20000 })
        .catch(() => {});
      if (errors.length) throw new Error(errors.join("; "));
      const shot = await page.evaluate(() => window.READY);
      if (!shot) throw new Error("the template did not finish (no done())");
      const stage = page.locator("#stage");
      const png = await stage.screenshot({
        omitBackground: shot.transparent,
        animations: "disabled",
      });
      const one = await encode(encoder, png, shot.width, shot.budget1x ?? BUDGET["1x"]);
      const two = await encode(encoder, png, shot.width * 2, shot.budget2x ?? BUDGET["2x"]);
      writeFileSync(join(OUT, `${name}.webp`), Buffer.from(one.b64, "base64"));
      writeFileSync(join(OUT, `${name}-2x.webp`), Buffer.from(two.b64, "base64"));
      const pct = ([x, y]) => [
        +((x / shot.width) * 100).toFixed(2),
        +((y / shot.height) * 100).toFixed(2),
      ];
      manifest[name] = {
        width: one.width,
        height: one.height,
        callouts: shot.callouts.map((c) => ({
          id: c.id,
          from: pct(c.from),
          to: pct(c.to),
          place: c.place,
          bend: c.bend,
          ...(c.max ? { max: c.max } : {}),
        })),
        ...(shot.lettering
          ? {
              lettering: [
                ...pct([shot.lettering[0], shot.lettering[1]]),
                ...pct([shot.lettering[2], shot.lettering[3]]),
              ],
            }
          : {}),
      };
      const kb = (b) => ((b.length * 3) / 4 / 1024).toFixed(0);
      console.log(
        `${name}  ${one.width} x ${one.height}  1x ${kb(one.b64)} KB (q ${one.q})  2x ${kb(two.b64)} KB (q ${two.q})`,
      );
      for (const w of shot.warnings) console.warn(`  ! ${w}`);
      if (PREVIEW) {
        await page.evaluate(
          (html) => document.getElementById("stage").insertAdjacentHTML("beforeend", html),
          previewOverlay(shot),
        );
        await stage.screenshot({ path: join(PREVIEW, `${name}.png`), omitBackground: false });
      }
    } catch (e) {
      failed++;
      console.error(`${name}: ${e instanceof Error ? e.message.split("\n")[0] : e}`);
    } finally {
      await ctx.close();
    }
  }
  await browser.close();
  const sorted = Object.fromEntries(
    Object.entries(manifest).sort(([a], [b]) => a.localeCompare(b)),
  );
  // short number lists on one line, as prettier writes them
  const json = JSON.stringify(sorted, null, 2).replace(
    /\[\s+([-\d.,\s]+?)\s+\]/g,
    (_, inner) => `[${inner.split(/,\s*/).join(", ")}]`,
  );
  writeFileSync(MANIFEST, `${json}\n`);
  if (failed) process.exit(1);
}

await main();

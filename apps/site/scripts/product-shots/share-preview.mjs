#!/usr/bin/env node
/**
 * The link preview in Tuesday's team chat (start page, components/phone-chat.tsx):
 * public/media/teilen-vorschau-{de,fr,en}.webp. Rendered by the app's own share picture renderer
 * (apps/web src/lib/share/og-image.tsx, the picture a shared link gets in WhatsApp and co.) for
 * the demo collection «Aussen rechts zumachen» (4 scenes, 1 minute) of HC Tannengrün Herren 1,
 * with the app's translations of each language. The collection's title and the team are written
 * in the visitor's language, as a coach of that language would name them; everything else is the
 * renderer's. No app, database or network needed:
 *
 *   node apps/site/scripts/product-shots/share-preview.mjs
 *
 * The site's chat texts (`home.chat.previewTitle`, `previewText` in src/messages) say the same.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadChromium } from "./playwright.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const ROOT = join(here, "../../../..");
const WEB = join(ROOT, "apps/web");
const OUT = join(ROOT, "apps/site/public/media");
/** shown at most 18.5rem wide in the chat bubble: 640 px covers it at twice the density */
const WIDTH = 640;

/** what the API's preview gives for the collection, in each language */
const PREVIEWS = {
  de: { app: "de-CH", title: "Aussen rechts zumachen", team: "Herren 1" },
  fr: { app: "fr", title: "Fermer l'aile droite", team: "Hommes 1" },
  en: { app: "en", title: "Close the right wing", team: "Men 1" },
};

// vite comes with the app's vitest, the translator with its next-intl
const require = createRequire(join(WEB, "package.json"));
const via = (pkg, name) => createRequire(require.resolve(pkg)).resolve(name);
const { createServer } = await import(via("vitest", "vite"));
const { createTranslator } = await import(via("next-intl", "use-intl"));

// the renderer as the app runs it: TSX with the app's «@/» paths; «server-only» only guards
// against the browser and is empty here
const vite = await createServer({
  root: WEB,
  configFile: false,
  logLevel: "error",
  server: { middlewareMode: true, hmr: false },
  appType: "custom",
  // the app's tsconfig keeps JSX for Next.js; here it becomes React calls
  oxc: { jsx: { runtime: "automatic" } },
  resolve: { alias: { "@": join(WEB, "src"), "server-only": join(here, "assets/empty.mjs") } },
  ssr: { noExternal: ["@handball/court", "@handball/tactics"] },
});

const chromium = await loadChromium();
const exe = process.env.PLAYWRIGHT_CHROMIUM_PATH;
const browser = await chromium.launch(exe ? { executablePath: exe } : {});
const page = await browser.newPage();
const prevCwd = process.cwd();
process.chdir(WEB); // the renderer reads its fonts from src/fonts of the app
try {
  const { sharePicture } = await vite.ssrLoadModule(join(WEB, "src/lib/share/og-image.tsx"));
  for (const [site, p] of Object.entries(PREVIEWS)) {
    const messages = JSON.parse(readFileSync(join(WEB, `messages/${p.app}.json`), "utf8"));
    const t = createTranslator({ locale: p.app, messages });
    const preview = {
      kind: "collection",
      title: p.title,
      club: "HC Tannengrün",
      team: p.team,
      opponent: null,
      score: null,
      scenes: 4,
      duration_s: 62,
      kit: { a: "#10684a", b: "#ffffff" },
    };
    const res = await sharePicture(preview, t, p.app);
    const png = Buffer.from(await res.arrayBuffer());
    // PNG to WebP in the browser, at the size the chat shows it
    const b64 = await page.evaluate(
      async ({ src, width }) => {
        const img = new Image();
        img.src = `data:image/png;base64,${src}`;
        await img.decode();
        const c = document.createElement("canvas");
        c.width = width;
        c.height = Math.round((img.naturalHeight * width) / img.naturalWidth);
        const g = c.getContext("2d");
        g.imageSmoothingQuality = "high";
        g.drawImage(img, 0, 0, c.width, c.height);
        return c.toDataURL("image/webp", 0.9).split(",")[1];
      },
      { src: png.toString("base64"), width: WIDTH },
    );
    const buf = Buffer.from(b64, "base64");
    writeFileSync(join(OUT, `teilen-vorschau-${site}.webp`), buf);
    console.log(`teilen-vorschau-${site}.webp  ${(buf.length / 1024).toFixed(1)} KB`);
  }
} finally {
  process.chdir(prevCwd);
  await browser.close();
  await vite.close();
}

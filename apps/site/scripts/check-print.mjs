// Prints the templates and the hall notice of the built site to PDF (Chromium, A4 from the page's
// @page rule) and checks that each fits on exactly one sheet. Needs Playwright with Chromium; it is
// not a dependency of the site, so this runs by hand after a build:
//
//   node scripts/check-print.mjs            (uses out/)
//
// Prints «path: n pages» for each and exits 1 if one needs more than one page.
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { createRequire } from "node:module";
import { dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = process.argv[2] ?? join(root, "out");
const PATHS = ["vorlagen/einwilligung", "vorlagen/strichliste", "vorlagen/spieltag", "aufnahme"];
const LOCALES = ["de", "fr", "en"];

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch {
    // the pre-installed global copy (cloud sessions) or a workspace copy of another app
    for (const base of ["/opt/node22/lib/node_modules/", join(root, "..", "web", "node_modules") + "/"]) {
      try {
        return createRequire(base)("playwright");
      } catch {
        /* next */
      }
    }
  }
  return null;
}

const TYPES = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".json": "application/json" };

const pw = await loadPlaywright();
if (!pw) {
  console.error("check-print: Playwright not found; skipped");
  process.exit(0);
}
if (!existsSync(out)) {
  console.error(`check-print: ${out} does not exist; build first`);
  process.exit(1);
}
const server = createServer((req, res) => {
  let p = join(out, decodeURIComponent((req.url ?? "/").split("?")[0]));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, "index.html");
  if (!existsSync(p)) {
    res.writeHead(404).end();
    return;
  }
  res.writeHead(200, { "Content-Type": TYPES[extname(p)] ?? "application/octet-stream" });
  createReadStream(p).pipe(res);
}).listen(0);
const port = server.address().port;
const browser = await pw.chromium.launch();
const page = await browser.newPage();
let bad = 0;
for (const l of LOCALES) {
  for (const p of PATHS) {
    await page.goto(`http://localhost:${port}/${l}/${p}/`, { waitUntil: "networkidle" });
    await page.emulateMedia({ media: "print" });
    const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });
    const pages = (pdf.toString("latin1").match(/\/Type\s*\/Page(?!s)/g) ?? []).length;
    if (pages !== 1) bad++;
    console.log(`check-print: /${l}/${p}/: ${pages} page${pages === 1 ? "" : "s"}`);
  }
}
await browser.close();
server.close();
process.exit(bad ? 1 : 0);

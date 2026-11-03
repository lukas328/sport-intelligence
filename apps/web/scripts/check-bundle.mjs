// Bundle budget (BRIEF 7.3): first-load JavaScript per route, gzip, from the production build.
// The start page must stay under 250 kB; every other route under 300 kB. Run after `next build`.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const BUDGET_START = 250 * 1024;
const BUDGET_ROUTE = 300 * 1024;
const next = join(import.meta.dirname, "..", ".next");
const manifest = JSON.parse(readFileSync(join(next, "app-build-manifest.json"), "utf8"));
const layout = manifest.pages["/layout"] ?? [];
const cache = new Map();
const gz = (file) => {
  if (!cache.has(file)) cache.set(file, gzipSync(readFileSync(join(next, file))).length);
  return cache.get(file);
};
const rows = [];
let failed = false;
for (const [page, files] of Object.entries(manifest.pages)) {
  if (!page.endsWith("/page")) continue;
  // route groups like (site) do not appear in the URL
  const route = page.replace(/\/page$/, "").replace(/\/\([^)]+\)/g, "") || "/";
  const all = [...new Set([...layout, ...files])].filter((f) => f.endsWith(".js"));
  const size = all.reduce((sum, f) => sum + gz(f), 0);
  const budget = route === "/" ? BUDGET_START : BUDGET_ROUTE;
  const over = size > budget;
  failed ||= over;
  rows.push([route, size, budget, over]);
}
rows.sort((a, b) => b[1] - a[1]);
for (const [route, size, budget, over] of rows) {
  console.log(`${over ? "OVER" : "ok  "} ${(size / 1024).toFixed(1).padStart(7)} kB / ${budget / 1024} kB  ${route}`);
}
if (failed) {
  console.error("bundle budget exceeded");
  process.exit(1);
}

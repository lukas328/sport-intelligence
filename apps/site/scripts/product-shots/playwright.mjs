import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

/** Playwright from the site, the repository root or the app's end-to-end tests (@playwright/test). */
export async function loadChromium() {
  for (const base of [
    join(here, "..", "..", "package.json"),
    join(here, "..", "..", "..", "..", "package.json"),
    join(here, "..", "..", "..", "web", "package.json"),
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

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const root = join(__dirname, "..", "..");
const out = join(root, "out");

describe("built site (scripts/check-out.mjs)", () => {
  // the build runs the same script; here it runs only when out/ is there (after a build)
  it.skipIf(!existsSync(join(out, "sitemap.xml")))("has no problems in out/", () => {
    const run = () => execFileSync("node", [join(root, "scripts", "check-out.mjs"), out], { encoding: "utf8", stdio: "pipe" });
    expect(run).not.toThrow();
  });
});

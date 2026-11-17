import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { COURT, contrastRatio, DEMO_CLUB, GROUND, kit, kitVars, PAPER } from "./color";

const root = join(__dirname, "..", "..", "..", "..");

describe("the demo club's colour, the website's own green (BEFUNDE-2 S11)", () => {
  it("carries white text and reads as text on the cloth, so the app shows it unchanged", () => {
    expect(contrastRatio(DEMO_CLUB, "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(DEMO_CLUB, GROUND)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(DEMO_CLUB, PAPER)).toBeGreaterThanOrEqual(4.5);
    const k = kit([DEMO_CLUB, "#ffffff"], ["#17191c", "#ffffff"]);
    expect(k.clubInk).toBe("#ffffff");
    expect(k.clubText).toBe(DEMO_CLUB);
    // the tactics camera draws it as it is, on the website's court and on the app's navy one
    expect(k.clubCam).toBe(DEMO_CLUB);
    expect(contrastRatio(DEMO_CLUB, COURT)).toBeGreaterThanOrEqual(2.2);
    expect(contrastRatio(DEMO_CLUB, "#0f2333")).toBeGreaterThanOrEqual(2.2);
  });

  it("is the same in the seed, the website's defaults and the product pictures' stage", () => {
    expect(readFileSync(join(root, "scripts", "seed.py"), "utf8").match(/"primary_color": "(#[0-9a-f]{6})"/)?.[1]).toBe(DEMO_CLUB);
    const css = readFileSync(join(__dirname, "..", "app", "globals.css"), "utf8");
    const vars = kitVars(kit([DEMO_CLUB, "#ffffff"], ["#17191c", "#ffffff"]));
    for (const [name, value] of Object.entries(vars)) expect(css, name).toContain(`${name}: ${value};`);
    expect(css).toContain(`--court: ${COURT};`);
    const stage = readFileSync(join(__dirname, "..", "..", "scripts", "product-shots", "stage.css"), "utf8");
    expect(stage).toContain(`--club: ${DEMO_CLUB};`);
  });
});

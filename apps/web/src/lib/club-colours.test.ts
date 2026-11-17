import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { CLUB_COLOURS, contrastRatio, DEFAULT_CLUB, GROUND, hue, kit, kitVars, OPPONENT_UNKNOWN_ON_BLACK } from "./color";
import { deltaE, SIMILAR_DELTA_E } from "./kit";
import deCH from "../../messages/de-CH.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";

// the demo club of the website and the seed (scripts/seed.py)
const DEMO_GREEN = "#10684a";

describe("club colours (decision E8)", () => {
  it("offers about eight colours, each carrying white text at 4.5:1 (the app head writes white on it)", () => {
    expect(CLUB_COLOURS.length).toBeGreaterThanOrEqual(7);
    expect(CLUB_COLOURS.length).toBeLessThanOrEqual(9);
    for (const [key, hex] of CLUB_COLOURS) {
      expect(contrastRatio(hex, "#ffffff"), key).toBeGreaterThanOrEqual(4.5);
      expect(kit([hex]).clubInk, key).toBe("#ffffff");
    }
  });

  it("are varied: no two alike, the typical club colours are there", () => {
    const hexes = CLUB_COLOURS.map(([, h]) => h);
    expect(new Set(hexes).size).toBe(hexes.length);
    expect(CLUB_COLOURS.map(([k]) => k)).toEqual(expect.arrayContaining(["red", "blue", "green", "black"]));
    // a coach sees the difference at a glance: as far apart as two kits must be (lib/kit.ts),
    // also from the slate of a club without a colour
    const all = [...hexes, DEFAULT_CLUB];
    for (let i = 0; i < all.length; i++)
      for (let j = i + 1; j < all.length; j++) expect(deltaE(all[i]!, all[j]!), `${all[i]} ${all[j]}`).toBeGreaterThanOrEqual(SIMILAR_DELTA_E);
  });

  it("have a name in every language", () => {
    for (const messages of [deCH, fr, en]) {
      const names = messages.onboarding.shirt as Record<string, string>;
      for (const [key] of CLUB_COLOURS) expect(names[key], key).toBeTruthy();
    }
  });

  it("a club without a choice is a neutral slate: readable, no club's pick, not the demo's green", () => {
    expect(DEFAULT_CLUB).toBe("#475569");
    expect(contrastRatio(DEFAULT_CLUB, "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(DEFAULT_CLUB, GROUND)).toBeGreaterThanOrEqual(4.5);
    expect(DEFAULT_CLUB).not.toBe(DEMO_GREEN);
    expect(CLUB_COLOURS.map(([, h]) => h)).not.toContain(DEFAULT_CLUB);
    // grey, not a hue a club would pick
    expect(hue(DEFAULT_CLUB)).toBe(-1);
  });

  it("the unknown opponent stays apart from the slate club", () => {
    const k = kit([DEFAULT_CLUB]);
    expect(k.opp).toBe(OPPONENT_UNKNOWN_ON_BLACK);
    expect(contrastRatio(k.club, k.opp)).toBeGreaterThanOrEqual(2);
  });

  it("globals.css starts from the slate club (the values before a page sets its club)", () => {
    const css = readFileSync(join(__dirname, "..", "app", "globals.css"), "utf8");
    const vars = kitVars(kit([DEFAULT_CLUB]));
    for (const name of ["--club", "--club-ink", "--club-text", "--club-cam", "--opp", "--opp-ink"]) {
      const m = new RegExp(`^\\s*${name}:\\s*([^;]+);`, "m").exec(css);
      expect(m?.[1]?.trim().toLowerCase(), name).toBe(vars[name]);
    }
  });
});

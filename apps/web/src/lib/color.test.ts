import { describe, expect, it } from "vitest";
import { CLOTH, contrastRatio, KIT_INK, kitsClash, kitTheme, opponentShown, OPPONENT_UNKNOWN } from "./color";

// club colours to check every screen with
const KITS = {
  red: "#c8102e",
  blue: "#0b3d91",
  green: "#1b7a3e",
  yellow: "#ffd200",
  black: "#111111",
  white: "#ffffff",
  orange: "#f28c00",
} as const;

describe("kit theme", () => {
  for (const [name, a] of Object.entries(KITS)) {
    it(`keeps ${name} text readable on the cloth in both themes`, () => {
      const k = kitTheme({ a, b: "#ffffff" });
      // text on the shirt itself
      expect(contrastRatio(k.ink, k.a)).toBeGreaterThanOrEqual(4.5);
      for (const theme of ["light", "dark"] as const) {
        const text = k.text[theme];
        expect(contrastRatio(text.color, CLOTH[theme])).toBeGreaterThanOrEqual(4.5);
        // a shadow only where the kit colour cannot carry the text; then the text is ink
        if (text.shadow) {
          expect(text.color).toBe(KIT_INK[theme]);
          expect(text.shadow).toBe(k.a);
        }
      }
    });
  }

  it("falls back to ink with a kit-coloured shadow for white and yellow kits, and for black at night", () => {
    expect(kitTheme({ a: KITS.white }).text.light.shadow).toBe(KITS.white);
    expect(kitTheme({ a: KITS.yellow }).text.light.shadow).toBe(KITS.yellow);
    expect(kitTheme({ a: KITS.black }).text.dark.shadow).toBe(KITS.black);
    // strong colours keep their hue as text
    expect(kitTheme({ a: KITS.red }).text.light.shadow).toBeNull();
    expect(kitTheme({ a: KITS.blue }).text.light.shadow).toBeNull();
  });

  it("defaults the second colour and rejects broken input", () => {
    const k = kitTheme({ a: "not a colour" });
    expect(k.b).toBe("#ffffff");
    expect(k.a).toMatch(/^#[0-9a-f]{6}$/);
  });
});

describe("opponent colour", () => {
  it("never guesses an unknown colour", () => {
    expect(opponentShown(KITS.red, null)).toEqual({ color: OPPONENT_UNKNOWN, ink: "#ffffff", source: "unknown" });
    expect(opponentShown(KITS.red, undefined, KITS.blue).source).toBe("unknown");
  });

  it("shows the opponent in its colour when it differs from ours", () => {
    expect(opponentShown(KITS.red, KITS.blue)).toMatchObject({ color: KITS.blue, source: "first" });
    expect(opponentShown(KITS.white, KITS.black).source).toBe("first");
  });

  it("switches to the second colour, then to ink, when the colours clash (away kit rule)", () => {
    expect(kitsClash("#c8102e", "#d0142f")).toBe(true);
    expect(kitsClash(KITS.red, KITS.blue)).toBe(false);
    expect(opponentShown(KITS.red, "#b5121b", KITS.white)).toMatchObject({ color: KITS.white, source: "second" });
    expect(opponentShown(KITS.red, "#b5121b")).toMatchObject({ color: KIT_INK.light, source: "ink" });
    expect(opponentShown(KITS.red, "#b5121b", "#cc0f2a").source).toBe("ink");
    // white against white
    expect(opponentShown(KITS.white, "#fafafa", KITS.green)).toMatchObject({ color: KITS.green, source: "second" });
  });
});

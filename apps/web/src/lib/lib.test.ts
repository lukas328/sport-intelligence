import { describe, expect, it, vi } from "vitest";
import deCH from "../../messages/de-CH.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";
import { clubTheme, contrastRatio, contrastText } from "./color";
import { errorKey, fieldErrors, KNOWN_ERRORS } from "./errors";
import { enterApp, safeNext } from "./nav";

function keys(obj: object, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === "object" && v !== null ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

describe("messages", () => {
  it("have the same keys in all locales", () => {
    expect(keys(en).sort()).toEqual(keys(deCH).sort());
    expect(keys(fr).sort()).toEqual(keys(deCH).sort());
  });
  it("use no long dashes, and de-CH uses ss", () => {
    for (const m of [deCH, en, fr]) expect(JSON.stringify(m)).not.toMatch(/[–—]/);
    expect(JSON.stringify(deCH)).not.toContain("ß");
  });
  it("translate every known API error", () => {
    for (const code of [...KNOWN_ERRORS, "generic"]) expect(deCH.errors).toHaveProperty(code);
  });
});

describe("errors", () => {
  it("maps problem types", () => {
    expect(errorKey({ type: "urn:handball-platform:problem:email-taken" })).toBe("email-taken");
    expect(errorKey({ type: "urn:handball-platform:problem:something-new" })).toBe("generic");
    expect(errorKey(undefined)).toBe("generic");
  });
  it("extracts field errors", () => {
    expect(
      fieldErrors({ errors: [{ loc: ["body", "email"], msg: "Value error, bad" }, { loc: ["body", "email"], msg: "x" }] }),
    ).toEqual({ email: "bad" });
  });
});

describe("color", () => {
  it("computes contrast", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21);
    expect(contrastText("#ffd700")).toBe("#000000");
    expect(contrastText("#0b3d91")).toBe("#ffffff");
  });
  const CLUBS = ["#0b6bcb", "#c8102e", "#0f6b46", "#003366", "#111111", "#ffd100", "#ffffff", "#00a651"];

  it("keeps club colours readable in both themes", () => {
    for (const hex of CLUBS) {
      const t = clubTheme(hex);
      expect(contrastRatio(t.light.accent, t.light.surface), hex).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(t.light.accent, t.light.paper), hex).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(t.dark.accent, t.dark.surface), hex).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(t.light.accent, t.light.contrast), hex).toBeGreaterThanOrEqual(4.5);
    }
    expect(clubTheme("#c8102e").light.accent).toBe("#c8102e");
    expect(clubTheme("#003366").dark.accent).not.toBe("#003366");
    expect(clubTheme("not a colour").club).toBe("#0b6bcb");
  });

  it("puts readable text on the stage, the deep surface and the signal", () => {
    for (const hex of CLUBS) {
      const t = clubTheme(hex);
      expect(contrastRatio(t.club, t.clubInk), hex).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(t.deep, "#ffffff"), hex).toBeGreaterThanOrEqual(7);
      expect(contrastRatio(t.signal, t.signalInk), hex).toBeGreaterThanOrEqual(7);
      // the signal must stand out from the stage it sits next to
      expect(contrastRatio(t.signal, t.club) > 1.3 || t.signal !== "#ffd23f", hex).toBe(true);
    }
    // yellow clubs: dark ink on the stage, neutral deep instead of olive, signal falls back to ink
    expect(clubTheme("#ffd100")).toMatchObject({ clubInk: "#10151c", deep: "#14171c", signal: "#10151c" });
    // the deep surface carries the club hue
    expect(clubTheme("#c8102e").deep).not.toBe(clubTheme("#0b6bcb").deep);
  });

  it("tints the paper towards the club colour", () => {
    expect(clubTheme("#c8102e").light.paper).not.toBe(clubTheme("#0b6bcb").light.paper);
    for (const hex of CLUBS) expect(contrastRatio(clubTheme(hex).light.paper, "#10151c")).toBeGreaterThanOrEqual(12);
  });
});

describe("safeNext", () => {
  it("only allows relative paths", () => {
    expect(safeNext("/app/x")).toBe("/app/x");
    expect(safeNext("//evil.com")).toBe("/app");
    expect(safeNext("https://evil.com")).toBe("/app");
    expect(safeNext("/\\evil.com")).toBe("/app");
    expect(safeNext(null)).toBe("/app");
  });
});

describe("enterApp", () => {
  it("loads the target as a new document after the session changed", () => {
    const location = { assign: vi.fn(), replace: vi.fn() };
    vi.stubGlobal("window", { location });
    try {
      enterApp("/app");
      expect(location.assign).toHaveBeenCalledWith("/app");
      enterApp("/login?totp=1", { replace: true });
      expect(location.replace).toHaveBeenCalledWith("/login?totp=1");
      expect(location.assign).toHaveBeenCalledTimes(1);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

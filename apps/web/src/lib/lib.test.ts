import { describe, expect, it, vi } from "vitest";
import deCH from "../../messages/de-CH.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";
import { clubTheme, contrastRatio, contrastText, SURFACE } from "./color";
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
  it("keeps club colours readable in both themes", () => {
    for (const hex of ["#ffd100", "#003366", "#c8102e", "#ffffff", "#000000", "#00a651"]) {
      const t = clubTheme(hex);
      expect(contrastRatio(t.light.accent, SURFACE.light)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(t.dark.accent, SURFACE.dark)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(t.light.accent, t.light.contrast)).toBeGreaterThanOrEqual(4.5);
    }
    // a readable club colour is kept as it is
    expect(clubTheme("#c8102e").light).toEqual({ accent: "#c8102e", contrast: "#ffffff" });
    // navy turns lighter on the dark theme instead of disappearing (1.49:1 before)
    expect(clubTheme("#003366").dark.accent).not.toBe("#003366");
    expect(clubTheme("not a colour").club).toBe("#c93a0b");
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

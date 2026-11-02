import { describe, expect, it } from "vitest";
import deCH from "../../messages/de-CH.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";
import { accentFor, contrastRatio, contrastText } from "./color";
import { errorKey, fieldErrors, KNOWN_ERRORS } from "./errors";
import { safeNext } from "./nav";

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
  it("falls back for light club colours", () => {
    expect(accentFor("#ffd700").accent).toBe("#0b6bcb");
    expect(accentFor("#c8102e")).toEqual({ accent: "#c8102e", contrast: "#ffffff" });
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

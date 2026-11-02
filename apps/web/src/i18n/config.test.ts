import { describe, expect, it } from "vitest";
import { resolveLocale } from "./config";

describe("resolveLocale", () => {
  it("defaults to de-CH", () => {
    expect(resolveLocale(undefined)).toBe("de-CH");
    expect(resolveLocale("xx")).toBe("de-CH");
  });
  it("maps German variants to de-CH", () => {
    expect(resolveLocale("de")).toBe("de-CH");
    expect(resolveLocale("de-DE")).toBe("de-CH");
  });
  it("accepts en and fr", () => {
    expect(resolveLocale("en")).toBe("en");
    expect(resolveLocale("fr-CH")).toBe("fr");
  });
});

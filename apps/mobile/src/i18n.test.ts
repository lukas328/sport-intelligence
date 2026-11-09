import { describe, expect, it } from "vitest";
import { DICTS, translator } from "./i18n";

describe("app texts", () => {
  it("have the same keys and placeholders in every language", () => {
    const de = DICTS["de-CH"]!;
    for (const lang of ["fr", "en"]) {
      const d = DICTS[lang]!;
      expect(Object.keys(d).sort()).toEqual(Object.keys(de).sort());
      for (const k of Object.keys(de) as (keyof typeof de)[]) {
        const ph = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
        expect(ph(d[k]), `${lang}.${k}`).toEqual(ph(de[k]));
      }
    }
  });

  it("uses no long dashes and no sharp s", () => {
    for (const d of Object.values(DICTS)) for (const v of Object.values(d)) expect(v).not.toMatch(/[–—]/);
    for (const v of Object.values(DICTS["de-CH"]!)) expect(v).not.toContain("ß");
  });

  it("fills placeholders and falls back to German", () => {
    expect(translator("fr")("pending", { n: 3 })).toBe("3 pas encore envoyées");
    expect(translator("xx")("signIn")).toBe("Anmelden");
  });
});

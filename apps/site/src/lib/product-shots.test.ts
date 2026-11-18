import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
// @ts-expect-error: a plain module of the picture scripts, without types
import { COLOURS, DEMO_COLOUR, LANGS, NAMES } from "../../scripts/product-shots/variants.mjs";
import { DEMO_CLUB, SHIRTS } from "./color";
import { APP_LOCALE, LOCALES } from "./i18n";
import manifest from "./product-shots.json";
import { APP_SHOTS, appShot, productShot, type ShotName } from "./product-shots";

const PUBLIC = join(__dirname, "..", "..", "public", "product");

/** the files the manifest promises, by picture */
function promised(): string[] {
  const files: string[] = [];
  for (const [name, m] of Object.entries(manifest) as [string, { densities?: number[]; colours?: string[]; colourDensities?: number[] }][]) {
    const at = (base: string, d: number) => `${base}${d === 1 ? "" : `-${d}x`}.webp`;
    for (const d of m.densities ?? [1, 2]) files.push(at(name, d));
    for (const c of m.colours ?? []) for (const d of m.colourDensities ?? [1, 2]) files.push(at(`${name}-${c}`, d));
  }
  return files;
}

describe("the product pictures (scripts/product-shots, BEFUNDE-4 U44 and U45)", () => {
  it("has every file the manifest names, and no file it does not", () => {
    const want = promised();
    for (const f of want) expect(existsSync(join(PUBLIC, f)), f).toBe(true);
    const have = readdirSync(PUBLIC).filter((f) => f.endsWith(".webp"));
    expect(have.filter((f) => !want.includes(f))).toEqual([]);
  });

  it("shows every app picture in each language of the site, the app's words in it", () => {
    expect(Object.keys(LANGS).sort()).toEqual([...LOCALES].sort());
    for (const l of LOCALES) expect(LANGS[l]).toBe(APP_LOCALE[l]);
    for (const name of APP_SHOTS)
      for (const l of LOCALES) {
        const shot = productShot(appShot(name, l));
        expect(shot.src).toBe(`/product/${name}-${l}.webp`);
        // the same picture in each language: the same size, so the page does not move
        expect([shot.width, shot.height]).toEqual([productShot(appShot(name, "de")).width, productShot(appShot(name, "de")).height]);
      }
    // the demo data's names in each language: the club and the story stay
    expect(NAMES.de).toEqual({ team: "Herren 1", collection: "Aussen rechts zumachen" });
    expect(Object.keys(NAMES).sort()).toEqual([...LOCALES].sort());
  });

  it("makes the large pictures up to three times the density, so they stay sharp on wide screens", () => {
    for (const name of ["app-desktop", "get-video", "get-search", "get-season", "share"] as const)
      for (const l of LOCALES) expect(productShot(appShot(name, l)).srcSet, name).toContain(`-3x.webp ${productShot(appShot(name, l)).width * 3}w`);
  });

  it("paints the app in the website's shirts, green being the demo club's own", () => {
    expect(DEMO_COLOUR[0]).toBe(DEMO_CLUB);
    const site = Object.fromEntries(SHIRTS) as Record<string, string>;
    expect(Object.keys(COLOURS).sort()).toEqual(Object.keys(site).filter((k) => k !== "green").sort());
    for (const [k, [hex]] of Object.entries(COLOURS) as [string, string[]][])
      // blue: the app's palette blue, the site's #1f4fd6 reads as «not chosen» in the app
      expect(hex, k).toBe(k === "blue" ? "#1d4ed8" : site[k]);
  });

  it("takes the file of the visitor's shirt where there is one, else green", () => {
    const coloured = (Object.keys(manifest) as ShotName[]).find((n) => productShot(n).colours.length);
    if (!coloured) return;
    const c = productShot(coloured).colours[0]!;
    expect(productShot(coloured, c).src).toBe(`/product/${coloured}-${c}.webp`);
    expect(productShot(coloured, "green").src).toBe(`/product/${coloured}.webp`);
    expect(productShot(coloured, null).src).toBe(`/product/${coloured}.webp`);
    // a picture without colour files (video-phone stays green) keeps its green file
    expect(productShot("video-phone-de", "red").src).toBe("/product/video-phone-de.webp");
  });
});

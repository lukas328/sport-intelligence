/**
 * The product pictures in public/product, made by scripts/product-shots (capture.mjs, then
 * compose.mjs). Their sizes, densities, club colours and callouts come from product-shots.json,
 * which compose.mjs writes, so the pages stay right when the pictures are made again.
 */
import type { SHIRTS } from "@/lib/color";
import type { Locale } from "@/lib/i18n";
import manifest from "./product-shots.json";

export type ShotName = keyof typeof manifest;

/** a shirt of the website (lib/color.ts SHIRTS) */
export type Shirt = (typeof SHIRTS)[number][0];

/** Where a label sits ("r" right of its point, "tl" above and running right …). */
export type Place = "r" | "l" | "t" | "b" | "tl" | "tr" | "bl" | "br";

export type Callout = {
  id: string;
  /** the label's point, in per cent of the picture */
  from: [number, number];
  /** the spot the arrow points at, in per cent */
  to: [number, number];
  place: Place;
  bend: number;
  /** the widest the label may be, in per cent of the picture (default: under half) */
  max?: number;
};

export type Shot = {
  name: ShotName;
  width: number;
  height: number;
  src: string;
  srcSet: string;
  callouts: Callout[];
  /** where the website writes a word over the picture (the video: «Dein Spiel»), [x, y, w, h] in per cent */
  lettering?: [number, number, number, number];
  /** the shirts this picture is made in besides the demo club's green (U45) */
  colours: Shirt[];
  /** the places the app tour pulls out of it (U34), by id: [x, y, w, h] in per cent */
  marks: Record<string, [number, number, number, number]>;
};

type Entry = {
  width: number;
  height: number;
  /** the files: 1 is <name>.webp, 2 <name>-2x.webp, 3 <name>-3x.webp (default 1 and 2) */
  densities?: number[];
  /** the club colours it is made in too (<name>-<colour>.webp), at `colourDensities` */
  colours?: string[];
  colourDensities?: number[];
  callouts: Callout[];
  lettering?: [number, number, number, number];
  marks?: Record<string, [number, number, number, number]>;
};

/** the pictures of the app: made once per language, in the app's own words (BEFUNDE-4) */
export const APP_SHOTS = ["app-desktop", "video-phone", "app-result", "get-video", "get-search", "get-season", "share"] as const;
export type AppShot = (typeof APP_SHOTS)[number];

/** an app picture in the page's language: <name>-<locale> */
export function appShot(name: AppShot, locale: Locale): ShotName {
  return `${name}-${locale}`;
}

/** the file of a picture at a density: <base>.webp, <base>-2x.webp, <base>-3x.webp */
const file = (base: string, d: number) => `/product/${base}${d === 1 ? "" : `-${d}x`}.webp`;

/**
 * A product picture, in the club colour of `shirt` where it is made in it (the app pictures,
 * BEFUNDE-4 U45: the app plays in the club's colour), else in the demo club's green. Green
 * itself is the demo club's own: the files without a colour in the name.
 */
export function productShot(name: ShotName, shirt?: Shirt | null): Shot {
  const m = manifest[name] as Entry;
  const colours = (m.colours ?? []) as Shirt[];
  const coloured = Boolean(shirt && colours.includes(shirt));
  const base = coloured ? `${name}-${shirt}` : name;
  const densities = (coloured ? m.colourDensities : m.densities) ?? [1, 2];
  return {
    name,
    width: m.width,
    height: m.height,
    src: file(base, 1),
    srcSet: densities.map((d) => `${file(base, d)} ${m.width * d}w`).join(", "),
    callouts: m.callouts,
    lettering: m.lettering,
    colours,
    marks: m.marks ?? {},
  };
}

/**
 * The arrow of a callout in pixels of the 1x picture: a curve from the label to just before the
 * spot, and its head. The same curve compose.mjs draws for its previews.
 */
export function arrow(c: Callout, width: number, height: number): { line: string; head: string } {
  const ax = (c.from[0] / 100) * width;
  const ay = (c.from[1] / 100) * height;
  const tx = (c.to[0] / 100) * width;
  const ty = (c.to[1] / 100) * height;
  const mx = (ax + tx) / 2 - (ty - ay) * c.bend;
  const my = (ay + ty) / 2 + (tx - ax) * c.bend;
  // stop a little before the spot, so the head does not cover it
  const dx = tx - mx;
  const dy = ty - my;
  const len = Math.hypot(dx, dy) || 1;
  const ex = tx - (dx / len) * 5;
  const ey = ty - (dy / len) * 5;
  const ux = dx / len;
  const uy = dy / len;
  const size = 13;
  const wing = (s: number) => {
    const a = (s * 28 * Math.PI) / 180;
    const rx = ux * Math.cos(a) - uy * Math.sin(a);
    const ry = ux * Math.sin(a) + uy * Math.cos(a);
    return `${(ex - rx * size).toFixed(1)} ${(ey - ry * size).toFixed(1)}`;
  };
  const f = (v: number) => v.toFixed(1);
  return {
    line: `M${f(ax)} ${f(ay)}Q${f(mx)} ${f(my)} ${f(ex)} ${f(ey)}`,
    head: `M${wing(1)}L${f(ex)} ${f(ey)}L${wing(-1)}`,
  };
}

/**
 * The page's rem in a `sizes` attribute. A sizes attribute counts rem at the browser's base size,
 * but from 1920 px wide the page's root font grows with the screen up to 18 px at 2560
 * (globals.css, BEFUNDE-3 U4); this follows it, so the browser knows how wide a picture really is.
 */
export const ROOT_REM = "clamp(1rem, 1rem + (100vw - 120rem) / 320, 1.125rem)";

/** `n` rem of the page as a length for `sizes` */
export function rem(n: number): string {
  return `calc(${n} * ${ROOT_REM})`;
}

/**
 * How wide the pictures are shown (U44, measured with Playwright from 360 to 2560 px): a `sizes`
 * value per place. `border` is the ink frame (2 px on each side) when the picture has one.
 */
export const SHOT_SIZES = {
  /**
   * the page's column (.wrap): the screen less its margins (1 rem, from 768 px 2 rem), at most
   * 72 rem, from 1600 px 86 rem
   */
  column: (border = 0) =>
    [
      `(min-width: 1600px) calc(86 * ${ROOT_REM} - ${border}px)`,
      `(min-width: 1216px) calc(72rem - ${border}px)`,
      `(min-width: 768px) calc(100vw - 4rem - ${border}px)`,
      `calc(100vw - 2rem - ${border}px)`,
    ].join(", "),
  /** a column of at most `max` rem, else the screen less its margins (1 rem, from 768 px 2 rem) */
  narrow: (max: number, border = 4) =>
    `(min-width: 768px) min(${rem(max)} - ${border}px, 100vw - 4rem - ${border}px), min(${rem(max)} - ${border}px, 100vw - 2rem - ${border}px)`,
  /** at most `max` rem in one of two columns from 768 px (gap 4 rem, Daten), else the screen */
  half: (max: number, border = 4) =>
    `(min-width: 768px) min(${rem(max)} - ${border}px, (100vw - 8rem) / 2 - ${border}px), min(${rem(max)} - ${border}px, 100vw - 2rem - ${border}px)`,
  /**
   * the app tour's stage (components/app-tour.tsx): the stage (94 per cent of the screen, at most
   * 120 rem) less the text column (25 per cent, 21 to 34 rem), the gap and the room for the labels
   * (11.5 rem); and no taller than the stage leaves room for (90vh less 4 rem); `share`: the part
   * of that the picture takes (U34: 0.9, it steps back behind its cut-outs)
   */
  tour: (aspect: number, border = 4, share = 1) =>
    `calc(min(min(94vw, ${rem(120)}) - max(${rem(21)}, min(25vw, ${rem(34)})) - ${rem(11.5)}, (90vh - ${rem(4)}) * ${aspect.toFixed(3)}) * ${share} - ${border}px)`,
};

/** Relative luminance (WCAG 2.x) of a #rrggbb colour. */
export function luminance(hex: string): number {
  const rgb = parse(hex);
  if (!rgb) return 0;
  const channels = rgb.map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0]! + 0.7152 * channels[1]! + 0.0722 * channels[2]!;
}

function parse(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m?.[1]) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function toHex(rgb: number[]): string {
  return `#${rgb.map((c) => Math.round(c).toString(16).padStart(2, "0")).join("")}`;
}

/** Mixes `hex` with `target` (0 = hex, 1 = target). */
export function mix(hex: string, target: string, amount: number): string {
  const a = parse(hex);
  const b = parse(target);
  if (!a || !b) return hex;
  return toHex(a.map((c, i) => c + (b[i]! - c) * amount));
}

export function contrastRatio(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (l1 + 0.05) / (l2 + 0.05);
}

/** Text colour (black or white) with the better contrast on the club colour. */
export function contrastText(hex: string): "#000000" | "#ffffff" {
  return contrastRatio(hex, "#ffffff") >= contrastRatio(hex, "#000000") ? "#ffffff" : "#000000";
}

export const INK = "#10151c";
export const INK_DARK = "#eef1f5";
export const NEUTRAL_DEEP = "#14171c";
export const SIGNAL = "#ffd23f";
export const DEFAULT_CLUB = "#0b6bcb";
/** kept for older callers */
export const DEFAULT_ACCENT = DEFAULT_CLUB;

export function isLight(hex: string): boolean {
  return contrastText(hex) === "#000000";
}

/** Page colours of a club: paper tinted towards the club colour (light), near black tinted (dark). */
export function paperOf(club: string): { light: string; dark: string; surfaceLight: string; surfaceDark: string; raisedDark: string } {
  return {
    light: mix(club, "#ffffff", 0.93),
    surfaceLight: mix(club, "#ffffff", 0.86),
    dark: mix(club, "#07090c", 0.9),
    surfaceDark: mix(club, "#0d1015", 0.8),
    raisedDark: mix(club, "#0d1015", 0.86),
  };
}

/** Darkest page surfaces of the light and dark theme for the default club (see globals.css). */
export const SURFACE = { light: paperOf(DEFAULT_CLUB).surfaceLight, dark: paperOf(DEFAULT_CLUB).surfaceDark } as const;

/**
 * Shifts a club colour until it reaches `min` contrast on `surface` (WCAG 2.2 AA: 4.5 for text),
 * towards black on light pages and towards white on dark pages. The hue stays recognisable,
 * e.g. a navy club stays navy on white and turns light blue on the dark theme.
 */
export function readableOn(hex: string, surface: string, min = 4.5): string {
  if (!parse(hex)) return DEFAULT_CLUB;
  const toward = luminance(surface) > 0.5 ? "#000000" : "#ffffff";
  for (let step = 0; step <= 20; step++) {
    const c = mix(hex, toward, step * 0.05);
    if (contrastRatio(c, surface) >= min) return c;
  }
  return toward;
}

export interface ClubTheme {
  /** the club colour as entered: the stage surface */
  club: string;
  /** text on the club colour */
  clubInk: string;
  /** the club's own dark surface (sidebar); neutral for light club colours, which turn olive */
  deep: string;
  /** the one thing per screen that needs attention */
  signal: string;
  signalInk: string;
  light: { accent: string; contrast: string; paper: string; surface: string };
  dark: { accent: string; contrast: string; paper: string; surface: string; raised: string };
}

export function clubTheme(hex: string | null | undefined): ClubTheme {
  const club = hex && parse(hex) ? hex.toLowerCase() : DEFAULT_CLUB;
  const light = isLight(club);
  const p = paperOf(club);
  const accentLight = readableOn(club, p.surfaceLight);
  const accentDark = readableOn(club, p.surfaceDark);
  return {
    club,
    clubInk: light ? INK : "#ffffff",
    deep: light ? NEUTRAL_DEEP : mix(club, "#050c18", 0.78),
    signal: light ? INK : SIGNAL,
    signalInk: light ? "#ffffff" : INK,
    light: { accent: accentLight, contrast: contrastText(accentLight), paper: p.light, surface: p.surfaceLight },
    dark: { accent: accentDark, contrast: contrastText(accentDark), paper: p.dark, surface: p.surfaceDark, raised: p.raisedDark },
  };
}

/** CSS custom properties for a club scope (consumed by `.club` in globals.css). */
export function clubStyle(hex: string | null | undefined): Record<string, string> {
  const t = clubTheme(hex);
  return {
    "--club": t.club,
    "--club-ink": t.clubInk,
    "--deep": t.deep,
    "--signal": t.signal,
    "--signal-ink": t.signalInk,
    // marker of the current place on the deep surface: white, or the club colour when it is light.
    // Resin yellow stays reserved for the one thing on a screen that needs attention.
    "--mark": isLight(t.club) ? t.club : "#ffffff",
    "--accent-l": t.light.accent,
    "--accent-l-contrast": t.light.contrast,
    "--paper-l": t.light.paper,
    "--surface-l": t.light.surface,
    "--accent-d": t.dark.accent,
    "--accent-d-contrast": t.dark.contrast,
    "--paper-d": t.dark.paper,
    "--surface-d": t.dark.surface,
    "--raised-d": t.dark.raised,
  };
}

// ---- Trikot: the club's kit and the opponent's colour (docs/design/ux-reset/TRIKOT.md) ----------

export const KIT_PATTERNS = ["uni", "stripes", "hoops", "sash", "halves"] as const;
export type KitPattern = (typeof KIT_PATTERNS)[number];

/** Neutral page and ink of both themes (TRIKOT.md, section 5). */
export const CLOTH = { light: "#f6f5f2", dark: "#121416" } as const;
export const KIT_INK = { light: "#14171a", dark: "#f1f0ec" } as const;
/** The opponent's colour while nobody has said it: never a guess. */
export const OPPONENT_UNKNOWN = "#3d4449";

export interface Kit {
  a: string;
  b: string;
  pattern: KitPattern;
}

export interface KitText {
  /** numerals and names in the kit colour, at least 4.5:1 on the cloth */
  color: string;
  /** set when the kit colour itself cannot carry text (white, yellow on light; black on dark):
   * the text falls back to ink and the kit colour becomes its hard shadow */
  shadow: string | null;
}

export interface KitTheme {
  a: string;
  b: string;
  pattern: KitPattern;
  /** text on the first colour (ink or white) */
  ink: string;
  text: { light: KitText; dark: KitText };
}

function kitText(a: string, cloth: string, ink: string): KitText {
  // a colour too close to the cloth would have to change its hue to become readable
  if (contrastRatio(a, cloth) < 2) return { color: ink, shadow: a };
  return { color: readableOn(a, cloth), shadow: null };
}

function normalise(hex: string | null | undefined, fallback: string): string {
  return hex && parse(hex) ? hex.toLowerCase() : fallback;
}

/** Derived values of a club kit: text on the shirt, kit-coloured text on the page in both themes. */
export function kitTheme(kit: Partial<Kit> & { a: string }): KitTheme {
  const a = normalise(kit.a, DEFAULT_CLUB);
  const b = normalise(kit.b, "#ffffff");
  const pattern = KIT_PATTERNS.includes(kit.pattern as KitPattern) ? (kit.pattern as KitPattern) : "uni";
  return {
    a,
    b,
    pattern,
    ink: contrastRatio(a, "#ffffff") >= contrastRatio(a, KIT_INK.light) ? "#ffffff" : KIT_INK.light,
    text: { light: kitText(a, CLOTH.light, KIT_INK.light), dark: kitText(a, CLOTH.dark, KIT_INK.dark) },
  };
}

/** Too close to tell apart on a shirt: same measure and threshold as the kit warnings (lib/kit.ts). */
export function kitsClash(x: string, y: string): boolean {
  if (!parse(x) || !parse(y)) return false;
  return kitDistance(x, y) < 25;
}

function kitDistance(x: string, y: string): number {
  const lab = (hex: string) => {
    const [r, g, b] = parse(hex)!.map((c) => {
      const s = c / 255;
      return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    }) as [number, number, number];
    const f = (t: number) => (t > (6 / 29) ** 3 ? Math.cbrt(t) : t / (3 * (6 / 29) ** 2) + 4 / 29);
    const X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047;
    const Y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
    const Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
    return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))] as const;
  };
  const p = lab(x);
  const q = lab(y);
  return Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
}

export interface OpponentShown {
  /** the colour to draw the opponent in */
  color: string;
  /** text on that colour */
  ink: string;
  /** first: their colour; second: their second colour because the first clashes with ours;
   * ink: both clash or no second colour; unknown: nobody said it, nothing is guessed */
  source: "first" | "second" | "ink" | "unknown";
}

/**
 * The opponent as shown next to us (TRIKOT.md, clash rule): like a real away kit, an opponent
 * whose colour is too close to ours appears in its second colour, or in ink.
 */
export function opponentShown(own: string, first: string | null | undefined, second?: string | null): OpponentShown {
  const ink = (c: string) => (contrastRatio(c, "#ffffff") >= contrastRatio(c, KIT_INK.light) ? "#ffffff" : KIT_INK.light);
  if (!first || !parse(first)) return { color: OPPONENT_UNKNOWN, ink: "#ffffff", source: "unknown" };
  const a = first.toLowerCase();
  if (!kitsClash(own, a)) return { color: a, ink: ink(a), source: "first" };
  if (second && parse(second) && !kitsClash(own, second)) return { color: second.toLowerCase(), ink: ink(second), source: "second" };
  return { color: KIT_INK.light, ink: "#ffffff", source: "ink" };
}

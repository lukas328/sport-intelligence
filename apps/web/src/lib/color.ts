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

/** Darkest page surfaces of the light and dark theme (see globals.css). */
export const SURFACE = { light: "#f2f2ee", dark: "#1f221e" } as const;
export const DEFAULT_ACCENT = "#c93a0b";

/**
 * Shifts a club colour until it reaches `min` contrast on `surface` (WCAG 2.2 AA: 4.5 for text),
 * towards black on light pages and towards white on dark pages. The hue stays recognisable,
 * e.g. a navy club stays navy on white and turns light blue on the dark theme.
 */
export function readableOn(hex: string, surface: string, min = 4.5): string {
  if (!parse(hex)) return DEFAULT_ACCENT;
  const toward = luminance(surface) > 0.5 ? "#000000" : "#ffffff";
  for (let step = 0; step <= 20; step++) {
    const c = mix(hex, toward, step * 0.05);
    if (contrastRatio(c, surface) >= min) return c;
  }
  return toward;
}

export interface ClubTheme {
  /** the club colour as entered, for decorative use only (logo tile, stripe) */
  club: string;
  light: { accent: string; contrast: string };
  dark: { accent: string; contrast: string };
}

export function clubTheme(hex: string | null | undefined): ClubTheme {
  const club = hex && parse(hex) ? hex.toLowerCase() : DEFAULT_ACCENT;
  const light = readableOn(club, SURFACE.light);
  const dark = readableOn(club, SURFACE.dark);
  return {
    club,
    light: { accent: light, contrast: contrastText(light) },
    dark: { accent: dark, contrast: contrastText(dark) },
  };
}

/** CSS custom properties for a club scope (consumed by `.club` in globals.css). */
export function clubStyle(hex: string | null | undefined): Record<string, string> {
  const t = clubTheme(hex);
  return {
    "--club": t.club,
    "--accent-l": t.light.accent,
    "--accent-l-contrast": t.light.contrast,
    "--accent-d": t.dark.accent,
    "--accent-d-contrast": t.dark.contrast,
  };
}

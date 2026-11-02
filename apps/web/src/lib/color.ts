/** Relative luminance (WCAG 2.x) of a #rrggbb colour. */
export function luminance(hex: string): number {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m?.[1]) return 0;
  const n = parseInt(m[1], 16);
  const channels = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0]! + 0.7152 * channels[1]! + 0.0722 * channels[2]!;
}

export function contrastRatio(a: string, b: string): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (l1 + 0.05) / (l2 + 0.05);
}

/** Text colour (black or white) with the better contrast on the club colour. */
export function contrastText(hex: string): "#000000" | "#ffffff" {
  return contrastRatio(hex, "#ffffff") >= contrastRatio(hex, "#000000") ? "#ffffff" : "#000000";
}

/**
 * Accent for UI elements on a white page. Very light club colours (e.g. yellow) cannot be used
 * for text or borders with enough contrast (WCAG 2.2 AA, 3:1 for UI), so we fall back to the default.
 */
export function accentFor(hex: string, fallback = "#0b6bcb"): { accent: string; contrast: string } {
  const accent = contrastRatio(hex, "#ffffff") >= 3 ? hex : fallback;
  return { accent, contrast: contrastText(accent) };
}

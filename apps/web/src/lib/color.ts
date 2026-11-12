/**
 * Colour model of the Anlauf look (docs/design/ux-reset/ANLAUF.md, port of assets/anlauf-farbe.js).
 * Two teams, two colours, everything else ink on cloth. `kit()` turns the club's two colours and the
 * opponent's colours into every derived value; `kitVars()` hands them to CSS as custom properties.
 */

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

function parse(hex: string | null | undefined): [number, number, number] | null {
  if (!hex) return null;
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m?.[1]) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function toHex(rgb: number[]): string {
  return `#${rgb.map((c) => Math.max(0, Math.min(255, Math.round(c))).toString(16).padStart(2, "0")).join("")}`;
}

export function isColor(hex: string | null | undefined): hex is string {
  return parse(hex) !== null;
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

/** Text colour (black or white) with the better contrast on `hex`. */
export function contrastText(hex: string): "#000000" | "#ffffff" {
  return contrastRatio(hex, "#ffffff") >= contrastRatio(hex, "#000000") ? "#ffffff" : "#000000";
}

// ---- the neutrals (globals.css holds the same values) ------------------------------------------

export const INK = "#16171a";
export const INK_DARK = "#0a0d11";
export const GROUND = "#eceae5";
export const PAPER = "#f7f6f2";
export const ATTN = "#ffd23c";
export const COURT = "#0f2333";
/** the opponent while nobody has said its colour: grey, never a guess */
export const OPPONENT_UNKNOWN = "#646b73";
/** the unknown opponent next to a black club, which would swallow the grey */
export const OPPONENT_UNKNOWN_ON_BLACK = "#8b9198";
export const DEFAULT_CLUB = "#1f4fd6";
/** below this contrast two colours of the same family read as the same team on the court */
export const CAM_SAME_LIGHTNESS = 2.5;

/** The six club colours every screen is checked with (SPEC.md), first and second colour. */
export const CHECK_KITS = {
  blau: ["#1f4fd6", "#ffffff"],
  rot: ["#d3202e", "#ffffff"],
  gelb: ["#f6c500", "#17191c"],
  schwarz: ["#17191c", "#ffffff"],
  weiss: ["#ffffff", "#17191c"],
  gruen: ["#12804a", "#ffffff"],
} as const satisfies Record<string, readonly [string, string]>;

/** The opponent the check colours are shown against (the demo season's TV Thalwil): black and white. */
export const CHECK_OPPONENT = ["#17191c", "#ffffff"] as const;

/** Shifts `c` towards `to` until it reaches `need` contrast on `ground`. */
export function reach(c: string, ground: string, need: number, to: string): string {
  for (let i = 0; i <= 50; i++) {
    const m = mix(c, to, i * 0.02);
    if (contrastRatio(m, ground) >= need) return m;
  }
  return to;
}

/** Hue in degrees, -1 for greys, black and white. */
export function hue(hex: string): number {
  const rgb = parse(hex);
  if (!rgb) return -1;
  const [r, g, b] = rgb.map((v) => v / 255) as [number, number, number];
  const mx = Math.max(r, g, b);
  const mn = Math.min(r, g, b);
  const d = mx - mn;
  if (d < 0.15) return -1;
  const x = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (x * 60 + 360) % 360;
}

/** Two colours a spectator would mix up: hues closer than 45 degrees, or two greys of similar lightness. */
export function near(a: string, b: string): boolean {
  const ha = hue(a);
  const hb = hue(b);
  if (ha < 0 || hb < 0) return ha < 0 && hb < 0 && Math.abs(luminance(a) - luminance(b)) < 0.25;
  const d = Math.abs(ha - hb);
  return Math.min(d, 360 - d) < 45;
}

/** White or ink on `c`, whichever is stronger. */
export function inkOn(c: string): string {
  return contrastRatio(c, "#ffffff") >= contrastRatio(c, INK) ? "#ffffff" : INK;
}

export type TwoColours = readonly [string, string];

export interface Kit {
  ground: string;
  club: string;
  club2: string;
  /** text on the club colour */
  clubInk: string;
  /** ink edge for a club colour that vanishes on the ground (white) */
  clubEdge: string;
  clubLine: string;
  /** piping of own lines when the club colour is too light on the ground; null without */
  clubPipe: string | null;
  /** the club colour as text (numerals, names) at 4.5:1 on the ground */
  clubText: string;
  oppKnown: boolean;
  /** the colour the opponent is drawn in (after the clash rule) */
  opp: string;
  opp2: string;
  /** which of the opponent's colours is shown: first, second (clash), ink (both clash), unknown */
  oppSource: "first" | "second" | "ink" | "unknown";
  oppInk: string;
  oppEdge: string;
  oppLine: string;
  oppPipe: string | null;
  /** tactics camera (dark court) */
  clubCam: string;
  clubCamInk: string;
  /** the teams would look alike on the court: the opponent steps back to grey rings */
  camClash: boolean;
  oppCam: string;
  oppCamInk: string;
  oppCamEdge: string;
  oppCamTrail: string;
}

function clean(colours: readonly (string | null | undefined)[] | null | undefined, fallback: TwoColours): [string, string] {
  const a = colours?.[0];
  const b = colours?.[1];
  const first = isColor(a) ? `#${a.replace("#", "").toLowerCase()}` : fallback[0];
  const second = isColor(b) ? `#${b.replace("#", "").toLowerCase()}` : first === "#ffffff" ? INK : "#ffffff";
  return [first, second];
}

/**
 * Everything colour-related for one club against one opponent on the cloth ground.
 * `opp` null or without a valid first colour: unknown, shown grey; the screens ask.
 */
export function kit(
  club: readonly (string | null | undefined)[] | null | undefined,
  opp?: readonly (string | null | undefined)[] | null,
  ground: string = GROUND,
): Kit {
  const c = clean(club, [DEFAULT_CLUB, "#ffffff"]);
  const clubInk = inkOn(c[0]);
  const clubEdge = contrastRatio(c[0], ground) < 1.3 ? INK : c[0];
  const low = contrastRatio(c[0], ground) < 2.4;
  const clubPipe = low ? (contrastRatio(c[1], ground) >= 3 ? c[1] : INK) : null;
  const clubText = contrastRatio(c[0], ground) >= 4.5 ? c[0] : hue(c[0]) < 0 ? INK : reach(c[0], ground, 4.5, "#000000");

  const known = isColor(opp?.[0]);
  let o: string;
  let o2: string;
  let oppSource: Kit["oppSource"];
  if (!known) {
    o = luminance(c[0]) < 0.05 ? OPPONENT_UNKNOWN_ON_BLACK : OPPONENT_UNKNOWN;
    o2 = "#ffffff";
    oppSource = "unknown";
  } else {
    const [f, s] = clean(opp, [OPPONENT_UNKNOWN, "#ffffff"]);
    // as with real away kits: too close to the club, the opponent plays its second colour, else ink
    if (!near(f, c[0])) {
      o = f;
      o2 = s;
      oppSource = "first";
    } else if (!near(s, c[0])) {
      o = s;
      o2 = f;
      oppSource = "second";
    } else {
      o = INK;
      o2 = f;
      oppSource = "ink";
    }
  }
  const oppPipe = contrastRatio(o, ground) < 2.4 ? INK : null;
  const oppEdge = contrastRatio(o, ground) < 1.3 ? INK : o;

  // tactics camera: a colour that vanishes on the dark court plays in its second colour
  const cc = contrastRatio(c[0], COURT) >= 2.2 ? c[0] : c[1];
  const ocam = contrastRatio(o, COURT) >= 2.2 ? o : o2;
  // two teams must never look alike on the court: only the same colour family AND a similar
  // lightness clash (blue against navy, red against orange, white against white). Blue against
  // red does not: own dots are filled, the opponent's are rings, and the hues differ.
  const camClash = known && near(cc, ocam) && contrastRatio(cc, ocam) < CAM_SAME_LIGHTNESS;
  const ring = !known || camClash;
  return {
    ground,
    club: c[0],
    club2: c[1],
    clubInk,
    clubEdge,
    clubLine: c[0],
    clubPipe,
    clubText,
    oppKnown: known,
    opp: o,
    opp2: o2,
    oppSource,
    oppInk: inkOn(o),
    oppEdge,
    oppLine: o,
    oppPipe,
    clubCam: cc,
    clubCamInk: contrastRatio(cc, "#ffffff") >= 3 ? "#ffffff" : INK_DARK,
    camClash,
    oppCam: ring ? COURT : ocam,
    oppCamInk: ring ? "#ffffff" : luminance(ocam) > 0.4 ? INK_DARK : "#ffffff",
    oppCamEdge: ring ? "#a3aeb8" : luminance(ocam) > 0.5 ? "#e9eef2" : reach(ocam, COURT, 3, "#ffffff"),
    oppCamTrail: ring ? "#a3aeb8" : reach(ocam, COURT, 3, "#ffffff"),
  };
}

/** The kit as CSS custom properties (consumed by globals.css and the Anlauf components). */
export function kitVars(k: Kit): Record<string, string> {
  return {
    "--club": k.club,
    "--club-2": k.club2,
    "--club-ink": k.clubInk,
    "--club-edge": k.clubEdge,
    "--club-text": k.clubText,
    "--club-line": k.clubLine,
    "--club-pipe": k.clubPipe ?? "transparent",
    "--club-dot": k.clubPipe ?? k.clubLine,
    "--opp": k.opp,
    "--opp-ink": k.oppInk,
    "--opp-edge": k.oppEdge,
    "--opp-line": k.oppLine,
    "--opp-pipe": k.oppPipe ?? "transparent",
    "--opp-dot": k.oppPipe ?? k.oppLine,
    "--club-cam": k.clubCam,
    "--club-cam-ink": k.clubCamInk,
    "--opp-cam": k.oppCam,
    "--opp-cam-ink": k.oppCamInk,
    "--opp-cam-edge": k.oppCamEdge,
    "--opp-cam-trail": k.oppCamTrail,
  };
}

/** CSS custom properties for a club scope; the opponent stays unknown until a match says it. */
export function clubStyle(primary: string | null | undefined, secondary?: string | null): Record<string, string> {
  return kitVars(kit([primary, secondary]));
}

/** CSS custom properties for a match: our club against the opponent's colours (null: unknown). */
export function matchStyle(club: readonly (string | null | undefined)[], opp: readonly (string | null | undefined)[] | null): Record<string, string> {
  return kitVars(kit(club, opp));
}

import { COURT } from "@handball/court";
import { kit } from "./color";

export interface MatchCardData {
  club: string;
  team: string;
  date: string;
  own: number;
  opp: number;
  opponent: string;
  /** e.g. "Sieg gegen TV Muster" */
  line: string;
  /** at most two figures, e.g. ["71 % Würfe", "23 % Paraden"] */
  figures: string[];
  colour: string;
  /** "Demo-Daten" when the match is a demo */
  tag?: string | null;
}

const W = 1080;
const H = 1350;

function fontVar(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v ? `${v}, ${fallback}` : fallback;
}

/** Fit a single line of text into `max` px by lowering the size. */
function fit(ctx: CanvasRenderingContext2D, text: string, weight: number, size: number, family: string, max: number): number {
  let s = size;
  for (; s > 24; s -= 4) {
    ctx.font = `${weight} ${s}px ${family}`;
    if (ctx.measureText(text).width <= max) break;
  }
  return s;
}

/**
 * Draws the match card (4:5, 1080 x 1350) on a canvas: the club colour as the surface, the goal
 * area of a real court (packages/court) as the frame, club, team, date, score, opponent and at most
 * two figures. No people, no pictures. Returns the canvas; callers turn it into a PNG.
 */
export function drawMatchCard(canvas: HTMLCanvasElement, d: MatchCardData): HTMLCanvasElement {
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx) return canvas;
  const k = kit([d.colour]);
  const theme = { club: k.club, clubInk: k.clubInk };
  const ink = theme.clubInk;
  const display = fontVar("--font-display", "'Arial Narrow', sans-serif");
  const text = fontVar("--font-sans", "Arial, sans-serif");

  ctx.fillStyle = theme.club;
  ctx.fillRect(0, 0, W, H);

  // court: the right goal area seen from above, rotated so the goal sits at the bottom
  const scale = 36; // px per metre: the 9 m line stays below the text
  const toXY = ([x, y]: readonly [number, number]): [number, number] => [W / 2 + (y - COURT.width / 2) * scale, H - 36 - (COURT.length - x) * scale];
  const stroke = (name: string, width: number, alpha: number, dash: number[] = []) => {
    const pts = COURT.lines[name];
    if (!pts?.length) return;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = ink;
    ctx.lineWidth = width;
    ctx.setLineDash(dash);
    ctx.beginPath();
    pts.forEach((p, i) => {
      const [x, y] = toXY(p as [number, number]);
      if (i) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
    });
    ctx.stroke();
    ctx.restore();
  };
  stroke("free_throw_right", 5, 0.45, [22, 18]);
  stroke("goal_area_right", 6, 0.6);
  stroke("penalty_mark_right", 6, 0.6);
  stroke("goal_right", 16, 0.8);

  ctx.fillStyle = ink;
  ctx.textBaseline = "alphabetic";
  const left = 84;
  const max = W - 2 * left;

  ctx.font = `700 ${fit(ctx, d.club.toUpperCase(), 700, 64, display, max)}px ${display}`;
  ctx.fillText(d.club.toUpperCase(), left, 150);
  ctx.font = `500 38px ${text}`;
  ctx.fillText(`${d.team} · ${d.date}`, left, 205);
  if (d.tag) {
    ctx.font = `600 30px ${text}`;
    const w = ctx.measureText(d.tag).width + 36;
    ctx.save();
    ctx.globalAlpha = 0.9;
    ctx.lineWidth = 3;
    ctx.strokeStyle = ink;
    ctx.strokeRect(left, 240, w, 52);
    ctx.restore();
    ctx.fillText(d.tag, left + 18, 277);
  }

  const score = `${d.own}:${d.opp}`;
  const scoreSize = fit(ctx, score, 800, 330, display, max);
  ctx.font = `800 ${scoreSize}px ${display}`;
  ctx.fillText(score, left - 8, 720);

  ctx.font = `700 ${fit(ctx, d.line.toUpperCase(), 700, 76, display, max)}px ${display}`;
  ctx.fillText(d.line.toUpperCase(), left, 820);

  ctx.font = `600 40px ${text}`;
  let x = left;
  for (const f of d.figures.slice(0, 2)) {
    ctx.fillText(f, x, 905);
    x += ctx.measureText(f).width + 60;
  }
  return canvas;
}

export function cardFileName(team: string, opponent: string, date: string): string {
  const slug = (s: string) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^\w]+/g, "-").replace(/^-|-$/g, "");
  return `matchkarte-${slug(team)}-${slug(opponent)}-${slug(date)}.png`;
}

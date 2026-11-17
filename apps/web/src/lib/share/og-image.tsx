import "server-only";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { COURT } from "@handball/court";
import type { PlayDoc } from "@handball/tactics";
import { ImageResponse } from "next/og";
import type { ReactNode } from "react";
import { ATTN, GROUND, INK, kit, PAPER } from "@/lib/color";
import { threeThings } from "@/lib/three-things";
import { goalWords, matchMinute, OG_SIZE, type SharePreview } from "./meta";
import type { T } from "./text";

/**
 * The pictures of shared content (K20, R2), rendered on the server: the link preview of every
 * shared page (1200 x 630) and the Spielkarte for the chat (1080 x 1080). Flat club colours,
 * few and large elements, the one important thing in the middle (WhatsApp crops a square from
 * the centre). Teams, result, minute, zones and a play's drawing; never names, faces or frames.
 * Kanit 900 italic and Hanken Grotesk (SIL OFL, src/fonts; woff, which the renderer reads).
 */

const FONT_DIR = join(process.cwd(), "src/fonts");
let fonts: Promise<{ name: string; data: Buffer; weight: 500 | 700 | 900; style: "normal" | "italic" }[]> | null = null;

function loadFonts() {
  fonts ??= Promise.all([
    readFile(join(FONT_DIR, "kanit-latin-900-italic.woff")).then((data) => ({ name: "Kanit", data, weight: 900 as const, style: "italic" as const })),
    readFile(join(FONT_DIR, "hanken-grotesk-latin-500-normal.woff")).then((data) => ({ name: "Hanken", data, weight: 500 as const, style: "normal" as const })),
    readFile(join(FONT_DIR, "hanken-grotesk-latin-700-normal.woff")).then((data) => ({ name: "Hanken", data, weight: 700 as const, style: "normal" as const })),
  ]);
  return fonts;
}

const SLANT = { fontFamily: "Kanit", fontWeight: 900, fontStyle: "italic" as const };
const TEXT = { fontFamily: "Hanken", fontWeight: 500 };
const BOLD = { fontFamily: "Hanken", fontWeight: 700 };
const BRAND = "Handball Intelligence";

type Size = { width: number; height: number };

export interface CardData {
  club: string;
  team: string;
  opponent: string | null;
  score: readonly number[] | null;
  halftime?: readonly number[] | null;
  kickoffAt?: string | null;
  kit: { a?: string | null; b?: string | null };
  oppKit?: string | null;
  goals?: readonly { team: "own" | "opp"; zone: string | null }[] | null;
}

function teamLine(club: string, team: string): string {
  return club && club !== team && !team.startsWith(club) ? `${club} ${team}` : team || club;
}

/** A size that keeps a title on at most two lines. */
function titleSize(text: string, wide: number): number {
  const n = text.length;
  if (n <= wide * 0.45) return 84;
  if (n <= wide * 0.7) return 68;
  if (n <= wide) return 56;
  return 46;
}

function Court({ w, h, colour, opacity }: { w: number; h: number; colour: string; opacity: number }) {
  // the attacked half (x 20..40 m) with the goal at the right; 9 m line dashed
  const sx = w / 20;
  const sy = h / 20;
  const pts = (name: string) => (COURT.lines[name] ?? []).map(([x, y]) => `${((x - 20) * sx).toFixed(1)},${(y * sy).toFixed(1)}`).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ position: "absolute", top: 0, left: 0, opacity }}>
      <polyline points={pts("goal_area_right")} fill="none" stroke={colour} strokeWidth={6} />
      <polyline points={pts("free_throw_right")} fill="none" stroke={colour} strokeWidth={5} strokeDasharray="18 14" />
      <polyline points={pts("penalty_mark_right")} fill="none" stroke={colour} strokeWidth={6} />
      <polyline points={pts("goal_right")} fill="none" stroke={colour} strokeWidth={14} />
    </svg>
  );
}

function Footer({ left, colour }: { left: string; colour: string }) {
  return (
    <div style={{ position: "absolute", left: 56, right: 56, bottom: 30, display: "flex", justifyContent: "space-between", alignItems: "center", color: colour, fontSize: 26, ...TEXT }}>
      <span style={{ display: "flex", maxWidth: 820, overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{left}</span>
      <span style={{ display: "flex", ...BOLD, fontSize: 24 }}>{BRAND}</span>
    </div>
  );
}

/** Scene, collection, playlist, highlights: the club colour, a big middle, the title. */
function Poster({ p, t, big, label }: { p: SharePreview; t: T; big: ReactNode; label: string }) {
  const k = kit([p.kit.a, p.kit.b]);
  const title = p.kind === "scene" && p.goal ? goalWords(t, p.goal) : p.title;
  const score = p.score && p.score.length === 2 ? `${p.score[0]}:${p.score[1]}` : null;
  const context = [teamLine(p.club, p.team), p.opponent ? t("share.og.vs", { opponent: p.opponent }) : null, score].filter(Boolean).join(" · ");
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", position: "relative", background: k.club, color: k.clubInk }}>
      <div style={{ position: "absolute", top: 0, right: 0, width: 560, height: 560, display: "flex" }}>
        <Court w={560} h={560} colour={k.clubInk} opacity={0.14} />
      </div>
      <svg width="1200" height="630" viewBox="0 0 1200 630" style={{ position: "absolute", top: 0, left: 0, width: 1200, height: 630 }}>
        <polygon points="0,520 1200,470 1200,630 0,630" fill={GROUND} />
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 46, bottom: 170, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 80px" }}>
        <div style={{ display: "flex", fontSize: 28, ...BOLD }}>{label}</div>
        <div style={{ display: "flex", alignItems: "center", marginTop: 6 }}>{big}</div>
        <div style={{ display: "flex", textAlign: "center", justifyContent: "center", fontSize: titleSize(title, 34), lineHeight: 1, marginTop: 10, maxWidth: 1040, ...SLANT }}>{title}</div>
      </div>
      <Footer left={context} colour={INK} />
    </div>
  );
}

function PlayMark({ colour, ink, size }: { colour: string; ink: string; size: number }) {
  return (
    <div style={{ width: size, height: size, borderRadius: size, background: ink, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg width={size * 0.42} height={size * 0.42} viewBox="0 0 10 10" style={{ marginLeft: size * 0.06 }}>
        <polygon points="1,0 10,5 1,10" fill={colour} />
      </svg>
    </div>
  );
}

function scenePicture(p: SharePreview, t: T) {
  const k = kit([p.kit.a, p.kit.b]);
  const minute = matchMinute(p.goal?.minute);
  const big = minute != null ? <div style={{ display: "flex", fontSize: 170, lineHeight: 1, ...SLANT }}>{t("share.og.minute", { minute })}</div> : <PlayMark colour={k.club} ink={k.clubInk} size={170} />;
  return <Poster p={p} t={t} big={big} label={t("share.og.kindScene")} />;
}

function runPicture(p: SharePreview, t: T) {
  const minutes = p.duration_s ? Math.max(1, Math.round(p.duration_s / 60)) : null;
  const big = (
    <div style={{ display: "flex", alignItems: "baseline" }}>
      <span style={{ display: "flex", fontSize: 190, lineHeight: 1, ...SLANT }}>{p.scenes}</span>
      <span style={{ display: "flex", fontSize: 44, marginLeft: 18, ...BOLD }}>
        {t("share.og.scenes", { n: p.scenes }).replace(/^\d+\s*/, "")}
        {minutes ? ` · ${t("share.og.minutes", { n: minutes })}` : ""}
      </span>
    </div>
  );
  return <Poster p={p} t={t} big={big} label={t(p.kind === "playlist" ? "share.og.kindPlaylist" : "share.og.kindCollection")} />;
}

function highlightPicture(p: SharePreview, t: T) {
  const k = kit([p.kit.a, p.kit.b]);
  const score = p.score && p.score.length === 2 ? `${p.score[0]}:${p.score[1]}` : null;
  const big = (
    <div style={{ display: "flex", alignItems: "center" }}>
      <PlayMark colour={k.club} ink={k.clubInk} size={150} />
      {score && <span style={{ display: "flex", fontSize: 170, lineHeight: 1, marginLeft: 36, ...SLANT }}>{score}</span>}
    </div>
  );
  const shown = { ...p, title: p.opponent ? t("share.og.vs", { opponent: p.opponent }) : teamLine(p.club, p.team) };
  return <Poster p={shown} t={t} big={big} label={t("share.og.kindHighlight")} />;
}

/** The drawing of a play's first phase on a light court: tokens, ball and arrows. */
function playPicture(p: SharePreview, t: T) {
  const k = kit([p.kit.a, p.kit.b]);
  const doc = p.play?.doc as unknown as PlayDoc | undefined;
  const frame = doc?.frames?.[0];
  const full = doc?.court === "full";
  const W = full ? 860 : 450;
  const H = full ? 430 : 450;
  const x0 = full ? 0 : 20;
  const s = W / (full ? 40 : 20);
  const at = (x: number, y: number) => [(x - x0) * s, y * s] as const;
  const phases = doc?.frames?.length ?? 0;
  const lines = (name: string) => (COURT.lines[name] ?? []).filter(([x]) => full || x >= 19.9).map(([x, y]) => at(x, y).map((v) => v.toFixed(1)).join(",")).join(" ");
  const court = PAPER;
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", position: "relative", background: GROUND, color: INK }}>
      <svg width="1200" height="630" viewBox="0 0 1200 630" style={{ position: "absolute", top: 0, left: 0, width: 1200, height: 630 }}>
        <polygon points="0,0 320,0 250,630 0,630" fill={k.club} />
      </svg>
      <div style={{ position: "absolute", left: 40, top: 48, width: 250, display: "flex", flexDirection: "column", color: k.clubInk }}>
        <div style={{ display: "flex", fontSize: 24, ...BOLD }}>{t("share.og.kindPlay")}</div>
        {phases > 1 && <div style={{ display: "flex", fontSize: 26, marginTop: 8, ...TEXT }}>{t("share.og.phases", { n: phases })}</div>}
        <div style={{ display: "flex", fontSize: 24, marginTop: 28, lineHeight: 1.25, ...BOLD }}>{teamLine(p.club, p.team)}</div>
      </div>
      <div style={{ position: "absolute", left: (1200 - W) / 2 + 60, top: 40, width: W, height: H, display: "flex", overflow: "hidden", background: court, border: `4px solid ${INK}` }}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", top: 0, left: 0 }}>
          {["goal_area_right", "penalty_mark_right", ...(full ? ["goal_area_left", "center_line", "penalty_mark_left"] : [])].map((n) => (
            <polyline key={n} points={lines(n)} fill="none" stroke={INK} strokeWidth={4} />
          ))}
          {["free_throw_right", ...(full ? ["free_throw_left"] : [])].map((n) => (
            <polyline key={n} points={lines(n)} fill="none" stroke={INK} strokeWidth={3} strokeDasharray="14 10" />
          ))}
          <polyline points={lines("goal_right")} fill="none" stroke={INK} strokeWidth={12} />
          {frame?.arrows.map((a, i) => (
            <polyline
              key={i}
              points={a.points.map(([x, y]) => at(x, y).map((v) => v.toFixed(1)).join(",")).join(" ")}
              fill="none"
              stroke={INK}
              strokeWidth={5}
              strokeDasharray={a.kind === "pass" ? "12 9" : a.kind === "dribble" ? "4 6" : "none"}
            />
          ))}
        </svg>
        {frame?.tokens.map((tok) => {
          const [x, y] = at(tok.x, tok.y);
          const own = tok.side === "own";
          return (
            <div
              key={tok.id}
              style={{ position: "absolute", left: x - 26, top: y - 26, width: 52, height: 52, borderRadius: 52, display: "flex", alignItems: "center", justifyContent: "center", background: own ? k.club : court, color: own ? k.clubInk : INK, border: `4px solid ${own ? k.clubEdge : INK}`, fontSize: 20, ...BOLD }}
            >
              {tok.label.slice(0, 3)}
            </div>
          );
        })}
        {frame?.ball && <div style={{ position: "absolute", left: at(frame.ball.x, frame.ball.y)[0] - 11, top: at(frame.ball.x, frame.ball.y)[1] - 11, width: 22, height: 22, borderRadius: 22, background: ATTN, border: `3px solid ${INK}`, display: "flex" }} />}
      </div>
      <div style={{ position: "absolute", left: 300, right: 40, top: 40 + H + 18, display: "flex", justifyContent: "center", textAlign: "center", fontSize: p.title.length > 28 ? 40 : 52, lineHeight: 1, ...SLANT }}>{p.title}</div>
      <Footer left="" colour={INK} />
    </div>
  );
}

/** The three things of a match from its goals (zones), as on the match page. */
export function cardThings(t: T, goals: CardData["goals"]): { value: number; of: number | null; text: string }[] {
  const runs = (goals ?? []).map((g) => ({ team: g.team, zone: g.zone, run: [], shot: [0, 0] as const, confirmed: true }));
  return threeThings(runs).map((x) => ({
    value: x.value,
    of: x.of,
    text: t(x.key === "conceded_zone" ? "anlauf.thing_conceded_zone" : x.key === "scored_zone" ? "anlauf.thing_scored_zone" : "anlauf.thing_conceded_fast_breaks", { zone: x.zone ? t(`anlauf.zoneFrom.${x.zone}`) : "" }),
  }));
}

function dateOf(iso: string | null | undefined, locale: string): string | null {
  return iso ? new Intl.DateTimeFormat(locale, { weekday: "short", day: "numeric", month: "long", year: "numeric", timeZone: "Europe/Zurich" }).format(new Date(iso)) : null;
}

/**
 * The Spielkarte: result and the three things. Square for the chat (1080), wide as the preview
 * of a shared match report (1200 x 630, the result in the middle).
 */
export function MatchCard({ d, t, size, locale = "de-CH" }: { d: CardData; t: T; size: Size; locale?: string }) {
  const k = kit([d.kit.a, d.kit.b], d.oppKit ? [d.oppKit] : null);
  const score = d.score && d.score.length === 2 ? `${d.score[0]}:${d.score[1]}` : "-:-";
  const things = cardThings(t, d.goals);
  const own = teamLine(d.club, d.team);
  const date = dateOf(d.kickoffAt, locale);
  const half = d.halftime && d.halftime.length === 2 ? t("share.og.halftime", { score: `${d.halftime[0]}:${d.halftime[1]}` }) : null;
  const eyebrow = [t("share.og.kindMatch"), date, half].filter(Boolean).join(" · ");
  const thingRow = (x: (typeof things)[number], n: number, compact: boolean) => (
    <div key={n} style={compact ? { display: "flex", flexDirection: "column", alignItems: "flex-start", flex: 1, paddingRight: 20 } : { display: "flex", flexDirection: "row", alignItems: "baseline", marginTop: 18 }}>
      <div style={compact ? { display: "flex", alignItems: "baseline" } : { display: "flex", alignItems: "baseline", width: 250 }}>
        <span style={{ display: "flex", fontSize: compact ? 76 : 92, lineHeight: 1, color: k.clubText, ...SLANT }}>{x.value}</span>
        {x.of != null && <span style={{ display: "flex", fontSize: compact ? 24 : 32, marginLeft: 10, ...BOLD }}>{t("share.og.of", { n: x.of })}</span>}
      </div>
      <span style={{ display: "flex", fontSize: compact ? 28 : 40, lineHeight: 1.15, marginTop: compact ? 6 : 0, ...BOLD }}>{x.text}</span>
    </div>
  );
  if (size.width === size.height) {
    return (
      <div style={{ width: "100%", height: "100%", display: "flex", position: "relative", background: GROUND, color: INK }}>
        <svg width={size.width} height={size.height} viewBox={`0 0 ${size.width} ${size.height}`} style={{ position: "absolute", top: 0, left: 0, width: size.width, height: size.height }}>
          <polygon points={`0,0 ${size.width},0 ${size.width},530 0,590`} fill={k.club} />
        </svg>
        <div style={{ position: "absolute", top: 62, left: 72, right: 72, display: "flex", flexDirection: "column", color: k.clubInk }}>
          <div style={{ display: "flex", fontSize: 30, ...BOLD }}>{eyebrow}</div>
          <div style={{ display: "flex", fontSize: own.length > 22 ? 56 : 72, lineHeight: 1, marginTop: 26, ...SLANT }}>{own}</div>
          <div style={{ display: "flex", fontSize: 220, lineHeight: 0.95, marginTop: 6, ...SLANT }}>{score}</div>
          <div style={{ display: "flex", fontSize: (d.opponent ?? "").length > 22 ? 56 : 72, lineHeight: 1, ...SLANT }}>{d.opponent ?? ""}</div>
        </div>
        <div style={{ position: "absolute", top: 625, left: 72, right: 72, display: "flex", flexDirection: "column" }}>
          {things.length > 0 && <div style={{ display: "flex", fontSize: 40, ...SLANT }}>{t("share.og.things")}</div>}
          {things.map((x, n) => thingRow(x, n, false))}
        </div>
        <Footer left="" colour={INK} />
      </div>
    );
  }
  // wide: both teams in their colours, the result in the middle
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", position: "relative", background: GROUND, color: INK }}>
      <svg width="1200" height="630" viewBox="0 0 1200 630" style={{ position: "absolute", top: 0, left: 0, width: 1200, height: 630 }}>
        <polygon points="0,0 640,0 580,330 0,350" fill={k.club} />
        <polygon points="640,0 1200,0 1200,310 580,330" fill={k.opp} />
      </svg>
      <div style={{ position: "absolute", top: 34, left: 0, right: 0, display: "flex", justifyContent: "center", fontSize: 24, color: k.clubInk, ...BOLD }}>
        <span style={{ display: "flex", background: k.club, padding: "2px 12px" }}>{eyebrow}</span>
      </div>
      <div style={{ position: "absolute", top: 96, left: 40, width: 500, display: "flex", justifyContent: "flex-end", textAlign: "right", fontSize: own.length > 18 ? 44 : 58, lineHeight: 1, color: k.clubInk, ...SLANT }}>{own}</div>
      <div style={{ position: "absolute", top: 96, left: 660, width: 500, display: "flex", fontSize: (d.opponent ?? "").length > 18 ? 44 : 58, lineHeight: 1, color: k.oppInk, ...SLANT }}>{d.opponent ?? ""}</div>
      <div style={{ position: "absolute", top: 210, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ display: "flex", background: GROUND, border: `5px solid ${INK}`, padding: "0 34px", fontSize: 150, lineHeight: 1.05, ...SLANT }}>{score}</div>
      </div>
      <div style={{ position: "absolute", top: 430, left: 56, right: 56, display: "flex" }}>{things.map((x, n) => thingRow(x, n, true))}</div>
      <Footer left={things.length ? "" : t("share.og.noAccount")} colour={INK} />
    </div>
  );
}

function matchPicture(p: SharePreview, t: T, locale: string) {
  return (
    <MatchCard
      d={{ club: p.club, team: p.team, opponent: p.opponent ?? null, score: p.score ?? null, halftime: p.halftime ?? null, kickoffAt: p.kickoff_at ?? null, kit: p.kit, oppKit: p.opp_kit ?? null, goals: p.goals ?? null }}
      t={t}
      size={OG_SIZE}
      locale={locale}
    />
  );
}

/** The picture of a shared link (1200 x 630). */
export async function sharePicture(p: SharePreview | null, t: T, locale = "de-CH"): Promise<ImageResponse> {
  const body = !p
    ? (
        <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: GROUND, color: INK, fontSize: 64, ...SLANT }}>{BRAND}</div>
      )
    : p.kind === "match"
      ? matchPicture(p, t, locale)
      : p.kind === "play"
        ? playPicture(p, t)
        : p.kind === "highlight"
          ? highlightPicture(p, t)
          : p.kind === "scene"
            ? scenePicture(p, t)
            : runPicture(p, t);
  return new ImageResponse(body, { ...OG_SIZE, fonts: await loadFonts(), headers: { "cache-control": "public, max-age=300, s-maxage=3600" } });
}

/** The Spielkarte as a square PNG for the chat. */
export async function matchCardPicture(d: CardData, t: T, locale = "de-CH"): Promise<ImageResponse> {
  const size = { width: 1080, height: 1080 };
  return new ImageResponse(<MatchCard d={d} t={t} size={size} locale={locale} />, { ...size, fonts: await loadFonts(), headers: { "cache-control": "private, max-age=60" } });
}

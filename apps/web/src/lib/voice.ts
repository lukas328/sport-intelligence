/**
 * The stage states one thing, like someone in the dressing room would, and only what follows
 * from the data (docs/DESIGN.md, "Stimme"). Every function returns message keys and parameters;
 * without enough data it returns null and the caller shows a neutral title. xG stays marked as
 * an estimate in every text that uses it.
 */

export interface Line {
  key: string;
  params: Record<string, string | number>;
}
export interface Statement {
  headline: Line;
  evidence: Line | null;
}

export interface SeasonRow {
  score_own: number;
  score_opponent: number;
  xg: number;
  xg_against: number;
  kickoff_at: string;
}

const round1 = (v: number) => Math.round(v * 10) / 10;
const result = (r: Pick<SeasonRow, "score_own" | "score_opponent">) => (r.score_own > r.score_opponent ? "w" : r.score_own < r.score_opponent ? "l" : "d");

/**
 * Clear gap between goals and expected goals: at least 2 and at least 10 %. A gap of more than
 * double either way says more about the estimate than the team (e.g. 26 goals from 3.4 when the
 * shots were not tagged): then nothing is said.
 */
export function xgGap(goals: number, xg: number): "over" | "under" | null {
  if (xg <= 0) return null;
  if (goals > xg * 2 || goals < xg / 2) return null;
  const d = goals - xg;
  if (Math.abs(d) < Math.max(2, xg * 0.1)) return null;
  return d > 0 ? "over" : "under";
}

export function seasonStatement(rows: SeasonRow[]): Statement | null {
  if (rows.length === 0) return null;
  const sorted = [...rows].sort((a, b) => a.kickoff_at.localeCompare(b.kickoff_at));
  const results = sorted.map(result);
  // a run of three or more equal results at the end of the season so far
  let run = 1;
  for (let i = results.length - 2; i >= 0 && results[i] === results.at(-1); i--) run++;
  const w = results.filter((r) => r === "w").length;
  const d = results.filter((r) => r === "d").length;
  const l = results.filter((r) => r === "l").length;
  const record: Line = { key: "voice.record", params: { w, d, l } };
  if (run >= 3 && results.at(-1) !== "d") {
    return { headline: { key: results.at(-1) === "w" ? "voice.runWins" : "voice.runLosses", params: { n: run } }, evidence: record };
  }
  const goals = sorted.reduce((s, r) => s + r.score_own, 0);
  const xg = sorted.reduce((s, r) => s + r.xg, 0);
  const against = sorted.reduce((s, r) => s + r.score_opponent, 0);
  const xga = sorted.reduce((s, r) => s + r.xg_against, 0);
  const attack = xgGap(goals, xg);
  if (attack) {
    return {
      headline: { key: attack === "over" ? "voice.overXg" : "voice.underXg", params: {} },
      evidence: { key: "voice.xgEvidence", params: { goals, xg: round1(xg) } },
    };
  }
  const defence = xgGap(against, xga);
  if (defence === "under") {
    return { headline: { key: "voice.defenceHeld", params: {} }, evidence: { key: "voice.xgaEvidence", params: { against, xga: round1(xga) } } };
  }
  if (defence === "over") {
    return { headline: { key: "voice.defenceLeaked", params: {} }, evidence: { key: "voice.xgaEvidence", params: { against, xga: round1(xga) } } };
  }
  if (rows.length >= 2) {
    return { headline: { key: w > l ? "voice.moreWins" : w < l ? "voice.moreLosses" : "voice.level", params: {} }, evidence: record };
  }
  return null;
}

export interface MatchFacts {
  own: number | null;
  opp: number | null;
  opponent: string;
  xg?: number | null;
}

export function matchStatement(m: MatchFacts): Statement | null {
  if (m.own == null || m.opp == null) return null;
  const diff = m.own - m.opp;
  const key =
    diff >= 5 ? "voice.wonClear" : diff === 1 ? "voice.wonTight" : diff > 0 ? "voice.won" : diff === 0 ? "voice.draw" : diff === -1 ? "voice.lostTight" : diff <= -5 ? "voice.lostClear" : "voice.lost";
  const gap = m.xg != null ? xgGap(m.own, m.xg) : null;
  const evidence: Line | null = gap ? { key: gap === "over" ? "voice.matchOverXg" : "voice.matchUnderXg", params: { goals: m.own, xg: round1(m.xg!) } } : null;
  return { headline: { key, params: { opponent: m.opponent } }, evidence };
}

/**
 * The one figure to work on, against common reference values for adult handball (save rate 30 %,
 * shooting 55 %, 12 turnovers per match). These are reference values, not a league average, and
 * the page says so. Returns null when nothing is clearly below.
 */
export const REFERENCE = { save_pct: 0.3, shooting_pct: 0.55, turnovers: 12 } as const;
export type FocusMetric = keyof typeof REFERENCE;

export function focusMetric(t: { save_pct: number | null; shooting_pct: number | null; turnovers_per_match: number | null }): FocusMetric | null {
  const gaps: [FocusMetric, number][] = [];
  if (t.save_pct != null) gaps.push(["save_pct", (REFERENCE.save_pct - t.save_pct) / REFERENCE.save_pct]);
  if (t.shooting_pct != null) gaps.push(["shooting_pct", (REFERENCE.shooting_pct - t.shooting_pct) / REFERENCE.shooting_pct]);
  if (t.turnovers_per_match != null) gaps.push(["turnovers", (t.turnovers_per_match - REFERENCE.turnovers) / REFERENCE.turnovers]);
  const worst = gaps.filter(([, g]) => g >= 0.1).sort((a, b) => b[1] - a[1])[0];
  return worst ? worst[0] : null;
}

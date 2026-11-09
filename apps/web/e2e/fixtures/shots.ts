/**
 * Shot candidates as the API returns them for an analysed video with an official report, with an
 * invented opponent player. Real candidates need the ball analysis on real footage plus a report;
 * the e2e spec answers the browser with this list and keeps its state like the API does.
 */
import type { CandidateList } from "../../src/lib/goal-candidates";

const candidate = (id: string, t_ms: number, clock_s: number, over: Record<string, unknown> = {}) => ({
  id: `00000000-0000-4000-8000-0000000f${id.padStart(4, "0")}`,
  kind: "shot",
  video_asset_id: "00000000-0000-4000-8000-000000000999",
  t_ms,
  goal_ms: t_ms - 500,
  start_ms: Math.max(0, t_ms - 6000),
  end_ms: t_ms + 3000,
  score: 0.9,
  rate: 2,
  suggested_side: null,
  status: "open",
  side: null,
  event_id: null,
  period: 1,
  clock_s,
  known: null,
  outcome: null,
  suggestion: null,
  ...over,
});

export const reportShot = {
  event_id: "00000000-0000-4000-8000-000000000e51",
  side: "opponent",
  outcome: "save",
  penalty: false,
  number: 14,
  player_id: null,
  name: "Kurt Beispiel",
  period: 1,
  clock_s: 765,
  official_time: "12:45",
  t_ms: 5000,
  uncertainty_ms: 2000,
};

export function shotList(): CandidateList {
  const candidates = [
    candidate("1", 5000, 765, { suggestion: reportShot, suggested_side: "opponent" }),
    candidate("2", 12_000, 772),
    candidate("3", 20_000, 780),
  ];
  return {
    kind: "shot",
    template: null,
    rates: [2, 4, 6],
    default_rate: 4,
    counts: { total: 3, open: 3, open_by_rate: { "2": 3, "4": 3, "6": 3 }, confirmed: 0, rejected: 0, known: 0, suggested: 1 },
    candidates,
    official: {
      counts: { total: 24, confirmed: 0, suggested: 1, missing: 2, outside: 21 },
      shots: [{ ...reportShot, status: "suggested", candidate_id: candidates[0]!.id }],
    },
  } as unknown as CandidateList;
}

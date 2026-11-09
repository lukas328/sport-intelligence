import type { Schemas } from "@handball/api-client";
import { isOpen, type CandidateList, type CandidateSide } from "./goal-candidates";

/** Moments the video analysis proposes as shots (shot-candidates): the coach says who shot and
 * how it ended, or takes the official report's entry for that moment with one key. Same table and
 * review endpoint as the goal candidates. */
export type ShotOutcome = "goal" | "save" | "miss" | "post" | "blocked";
export type ShotCandidate = CandidateList["candidates"][number];
export type ReportShot = Schemas["OfficialShot"];
export type ShotFilter = "report" | "open" | "all";
export const OUTCOMES: ShotOutcome[] = ["goal", "save", "miss", "post", "blocked"];

/** The tagger's letters for the same outcomes, so a coach learns them once. */
export const OUTCOME_KEY: Record<ShotOutcome, string> = { goal: "G", save: "S", miss: "M", post: "P", blocked: "B" };

export type ShotKeyAction =
  | { kind: "side"; side: CandidateSide }
  | { kind: "outcome"; outcome: ShotOutcome }
  | { kind: "accept" | "reject" | "undo" | "play" | "next" | "prev" | "first" | "last" };

const KEYS: Record<string, ShotKeyAction> = {
  "1": { kind: "side", side: "own" },
  "2": { kind: "side", side: "opponent" },
  g: { kind: "outcome", outcome: "goal" },
  s: { kind: "outcome", outcome: "save" },
  m: { kind: "outcome", outcome: "miss" },
  p: { kind: "outcome", outcome: "post" },
  b: { kind: "outcome", outcome: "blocked" },
  Enter: { kind: "accept" },
  x: { kind: "reject" },
  Delete: { kind: "reject" },
  u: { kind: "undo" },
  Backspace: { kind: "undo" },
  r: { kind: "play" },
  " ": { kind: "play" },
  ArrowDown: { kind: "next" },
  ArrowUp: { kind: "prev" },
  Home: { kind: "first" },
  End: { kind: "last" },
};

export function shotKeyAction(key: string): ShotKeyAction | null {
  return KEYS[key] ?? KEYS[key.toLowerCase()] ?? null;
}

const asSide = (s: string | null | undefined): CandidateSide | null => (s === "own" || s === "opponent" ? s : null);
const asOutcome = (o: string | null | undefined): ShotOutcome | null => (OUTCOMES as string[]).includes(o ?? "") ? (o as ShotOutcome) : null;

/** The team the answer is for before the coach picks one: the report's, else the analysis'. */
export function defaultSide(c: ShotCandidate): CandidateSide | null {
  return asSide(c.suggestion?.side) ?? c.suggested_side;
}

/** "report": the open moments with a report entry (any rate: they are roughly the logged shots);
 * "open": what still needs a click at this rate; "all": also what was decided or is known. */
export function visibleShots(list: CandidateList, rate: number, filter: ShotFilter): ShotCandidate[] {
  return list.candidates.filter((c) =>
    filter === "report"
      ? isOpen(c) && c.suggestion != null
      : filter === "open"
        ? isOpen(c) && c.rate <= rate
        : c.rate <= rate || c.status !== "open",
  );
}

export type ShotReviewBody =
  | { status: "confirmed" } // pins the report's suggestion
  | { status: "confirmed"; side: CandidateSide; outcome: ShotOutcome }
  | { status: "rejected" }
  | { status: null };

/** The review an answer sends. With the report's side and outcome the entry is pinned (one event,
 * the report's player); anything else is the coach's own shot. Null when no team is known yet. */
export function shotAnswer(c: ShotCandidate, side: CandidateSide | null, outcome: ShotOutcome | "accept"): ShotReviewBody | null {
  const s = c.suggestion;
  if (outcome === "accept") return s ? { status: "confirmed" } : null;
  const who = side ?? defaultSide(c);
  if (!who) return null;
  if (s && asSide(s.side) === who && asOutcome(s.outcome) === outcome) return { status: "confirmed" };
  return { status: "confirmed", side: who, outcome };
}

/** The list with one answer applied, for an optimistic update of the cached list. */
export function withShotReview(list: CandidateList, id: string, body: ShotReviewBody): CandidateList {
  const candidates = list.candidates.map((c): ShotCandidate => {
    if (c.id !== id) return c;
    if (body.status !== "confirmed") return { ...c, status: body.status ?? "open", side: null, outcome: null };
    const side = "side" in body ? body.side : asSide(c.suggestion?.side);
    const outcome = "outcome" in body ? body.outcome : asOutcome(c.suggestion?.outcome);
    return { ...c, status: "confirmed", side, outcome };
  });
  const open = candidates.filter(isOpen);
  return {
    ...list,
    candidates,
    counts: {
      ...list.counts,
      open: open.length,
      open_by_rate: Object.fromEntries(list.rates.map((r) => [String(r), open.filter((c) => c.rate <= r).length])),
      confirmed: candidates.filter((c) => c.status === "confirmed").length,
      rejected: candidates.filter((c) => c.status === "rejected").length,
      suggested: open.filter((c) => c.suggestion != null).length,
    },
  };
}

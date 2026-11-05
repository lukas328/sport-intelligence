import type { Schemas } from "@handball/api-client";

/** Moments the video analysis proposes as goals (goal-candidates), with the coach's reviews. */
export type CandidateList = Schemas["GoalCandidateList"];
export type Candidate = Schemas["GoalCandidateRow"];
export type CandidateSide = "own" | "opponent";
export type CandidateReview = "confirmed" | "rejected";
export type CandidateFilter = "open" | "all";

/** What a key does on a focused candidate row. Letters the tagger and the player use (g, s, m,
 * p, t, k, j, l, f) are left alone. */
export type KeyAction =
  "own" | "opponent" | "reject" | "undo" | "play" | "next" | "prev" | "first" | "last";

const KEYS: Record<string, KeyAction> = {
  "1": "own",
  "2": "opponent",
  x: "reject",
  Delete: "reject",
  u: "undo",
  Backspace: "undo",
  Enter: "play",
  r: "play",
  " ": "play",
  ArrowDown: "next",
  ArrowUp: "prev",
  Home: "first",
  End: "last",
};

export function keyAction(key: string): KeyAction | null {
  return KEYS[key] ?? KEYS[key.toLowerCase()] ?? null;
}

/** Still to look at: open and not already a goal (overlay, report, tagged). */
export function isOpen(c: Candidate): boolean {
  return c.status === "open" && c.known == null;
}

/** The rows shown at a candidates-per-minute rate: "open" only what still needs a click, "all"
 * also what was reviewed or is already a goal (reviewed rows stay at any rate). */
export function visibleRows(
  list: CandidateList,
  rate: number,
  filter: CandidateFilter,
): Candidate[] {
  return list.candidates.filter((c) =>
    filter === "open" ? isOpen(c) && c.rate <= rate : c.rate <= rate || c.status !== "open",
  );
}

/** The candidate with its review changed, for an optimistic update of the cached list. */
export function withReview(
  list: CandidateList,
  id: string,
  status: CandidateReview | null,
  side: CandidateSide | null,
): CandidateList {
  const candidates = list.candidates.map((c): Candidate =>
    c.id === id
      ? { ...c, status: status ?? "open", side: status === "confirmed" ? side : null }
      : c,
  );
  const open = candidates.filter(isOpen);
  return {
    ...list,
    candidates,
    counts: {
      ...list.counts,
      open: open.length,
      open_by_rate: Object.fromEntries(
        list.rates.map((r) => [String(r), open.filter((c) => c.rate <= r).length]),
      ),
      confirmed: candidates.filter((c) => c.status === "confirmed").length,
      rejected: candidates.filter((c) => c.status === "rejected").length,
    },
  };
}

/** The row to focus after a review removed row `index` from the open list (the next one, else the
 * one before). */
export function focusAfter(length: number, index: number, removed: boolean): number {
  if (length <= 0) return -1;
  const next = removed ? index : index + 1;
  return Math.min(Math.max(0, next), length - 1 - (removed ? 1 : 0));
}

/** Row index after a navigation key. */
export function moveFocus(action: KeyAction, index: number, length: number): number {
  if (length <= 0) return -1;
  if (action === "first") return 0;
  if (action === "last") return length - 1;
  if (action === "next") return Math.min(length - 1, index + 1);
  if (action === "prev") return Math.max(0, index - 1);
  return index;
}

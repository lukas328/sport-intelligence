/**
 * The start's head after an analysis (real-video test, second round): a freshly analysed match
 * stands in the head until the coach has opened it, and as long as it has open questions, with
 * the result from the video and the next step. Otherwise the last match as before.
 */

const KEY = "hb_opened_matches";
/** an analysis older than this is not «fresh» any more, opened or not */
export const FRESH_DAYS = 7;

function read(): string[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    const list = raw ? (JSON.parse(raw) as unknown) : [];
    return Array.isArray(list) ? list.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function openedMatches(): Set<string> {
  return new Set(read());
}

/** the coach opened the match: it leaves the head once its questions are answered */
export function markOpened(matchId: string): void {
  try {
    const list = read().filter((x) => x !== matchId);
    window.localStorage.setItem(KEY, JSON.stringify([matchId, ...list].slice(0, 50)));
  } catch {
    // no storage (private window): the head then only follows the open questions
  }
}

export type FreshInfo = { id: string; analysis: string; analysisAt: string | null; checks: number };

/**
 * The match for the head: the newest played match whose analysis is done, finished within
 * FRESH_DAYS, and that either still has open questions or was not opened yet. Null: the last match.
 */
export function freshMatch(infos: FreshInfo[], opened: Set<string>, now: number): string | null {
  const limit = now - FRESH_DAYS * 86_400_000;
  const hit = infos.find((x) => x.analysis === "ready" && x.analysisAt != null && new Date(x.analysisAt).getTime() >= limit && (x.checks > 0 || !opened.has(x.id)));
  return hit?.id ?? null;
}

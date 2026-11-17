const HOUR = 3600_000;

/**
 * Whether «Spieltag starten» is the thing to do now: from three hours before the kick-off (arrive,
 * warm up, set up the phone) until three hours after it. Days before, it is a quiet action in the
 * menu; the coach sees the opponent there, not a big button (QA night, 17.11.).
 */
export function isMatchDay(kickoffAt: string | Date, now = Date.now()): boolean {
  const k = typeof kickoffAt === "string" ? Date.parse(kickoffAt) : kickoffAt.getTime();
  return now >= k - 3 * HOUR && now <= k + 3 * HOUR;
}

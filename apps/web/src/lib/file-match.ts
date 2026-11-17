/**
 * Does a second file belong to the same match (second round A5)? Two different games ended up in
 * one match (Horgen and Konstanz). Several files per match are wanted (halves, a split
 * recording), so this only warns: when the file names name different teams, or different dates.
 */

// words of file names that say nothing about the game
const NOISE = new Set([
  "mp4", "mov", "mkv", "m4v", "avi", "mts", "m2ts", "webm",
  "video", "spiel", "match", "game", "partie", "halbzeit", "half", "teil", "part", "clip",
  "camera", "kamera", "cam", "gopro", "img", "vid", "dji", "pxl", "mvi", "dsc",
  "full", "ganz", "ganzes", "copy", "kopie", "final", "edit", "export", "trim", "cut",
  "erste", "zweite", "first", "second", "liga", "league", "herren", "damen", "junioren",
  "handball", "the", "und", "and", "gegen", "vs", "versus",
]);

/** The words of a file name that may name a team or a place: letters only, CamelCase split
 * (HSGKonstanz: HSG, Konstanz), at least three letters, without the usual noise. */
export function nameWords(filename: string): string[] {
  const base = filename.replace(/\.[a-z0-9]{2,5}$/i, "");
  const words = base
    .replace(/([a-zäöü])([A-ZÄÖÜ])/g, "$1 $2")
    .replace(/([A-ZÄÖÜ]+)([A-ZÄÖÜ][a-zäöü])/g, "$1 $2")
    .split(/[^A-Za-zÄÖÜäöüéèàç]+/)
    .map((w) => w.toLowerCase())
    .filter((w) => w.length >= 3 && !NOISE.has(w));
  return [...new Set(words)];
}

/** A date in the file name (2026-11-15, 20261115, 15.11.2026), as yyyymmdd. */
export function nameDate(filename: string): string | null {
  const iso = filename.match(/(20\d\d)[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])/);
  if (iso) return `${iso[1]}${iso[2]}${iso[3]}`;
  const ch = filename.match(/(0?[1-9]|[12]\d|3[01])\.(0?[1-9]|1[0-2])\.(20\d\d)/);
  if (ch) return `${ch[3]}${ch[2]!.padStart(2, "0")}${ch[1]!.padStart(2, "0")}`;
  return null;
}

/**
 * The file of the match the new one probably does not belong with, or null: both names carry at
 * least two telling words and share none, or both carry a date and the dates differ. Camera
 * names (GX010123.MP4) carry no telling words and never warn.
 */
export function otherGame(filename: string, existing: string[]): string | null {
  const mine = nameWords(filename);
  const date = nameDate(filename);
  for (const other of existing) {
    if (other === filename) continue;
    const theirs = nameWords(other);
    const theirDate = nameDate(other);
    if (date && theirDate && date !== theirDate) return other;
    if (mine.length >= 2 && theirs.length >= 2 && !mine.some((w) => theirs.includes(w))) return other;
  }
  return null;
}

/**
 * Shirt numbers in the squad: with a squad that has them, the analysis names people by the
 * number it reads (audit #160: with a squad 48 % right, 0 % wrong; without numbers it cannot).
 * Who has none, which number two players share, and a quick way in: number and name per line.
 */

export interface NumberedEntry {
  jersey_number: number | null;
  first_name: string;
  last_name: string;
}

/** Players without a number, and numbers two or more players share (lowest number first). */
export function numberGaps<E extends NumberedEntry>(entries: readonly E[]): { without: E[]; duplicates: [number, E[]][] } {
  const by = new Map<number, E[]>();
  const without: E[] = [];
  for (const e of entries) {
    if (e.jersey_number == null) without.push(e);
    else by.set(e.jersey_number, [...(by.get(e.jersey_number) ?? []), e]);
  }
  const duplicates = [...by.entries()].filter(([, list]) => list.length > 1).sort(([a], [b]) => a - b);
  return { without, duplicates };
}

export interface QuickRow {
  line: number; // 1-based, as the coach sees it
  number: number | null;
  first: string;
  last: string;
  error: "name" | "number" | "twice" | null;
}

const NUM = /^#?(\d{1,2})\.?$/;

/**
 * A squad typed or pasted as lines: «7 Lena Muster», «#7 Lena Muster», «Lena Muster 7», or
 * columns from a spreadsheet («7<tab>Lena<tab>Muster», «7;Muster;Lena» with a header-less
 * Nr;Nachname;Vorname is not guessed: columns are number, first name, last name). Empty lines
 * are skipped. A row needs a first and a last name; a number from 1 to 99 or none.
 */
export function parseQuickRoster(text: string): QuickRow[] {
  const rows: QuickRow[] = [];
  const seen = new Map<number, number>();
  text.split(/\r?\n/).forEach((raw, i) => {
    const line = raw.trim();
    if (!line) return;
    let parts = /[\t;]/.test(line) ? line.split(/[\t;]/).map((p) => p.trim()).filter(Boolean) : line.split(/\s+/);
    let number: number | null = null;
    let bad = false;
    const first = parts[0] ?? "";
    const last = parts[parts.length - 1] ?? "";
    if (/^#?\d/.test(first)) {
      const m = NUM.exec(first);
      if (m) number = Number(m[1]);
      else bad = true;
      parts = parts.slice(1);
    } else if (/^#?\d/.test(last)) {
      const m = NUM.exec(last);
      if (m) number = Number(m[1]);
      else bad = true;
      parts = parts.slice(0, -1);
    }
    // «7 - Lena Muster»: a dash between number and name
    if (parts[0] === "-" || parts[0] === "–") parts = parts.slice(1);
    if (number != null && (number < 1 || number > 99)) bad = true;
    const name = { first: parts[0] ?? "", last: parts.slice(1).join(" ") };
    let error: QuickRow["error"] = bad ? "number" : !name.first || !name.last ? "name" : null;
    if (!error && number != null) {
      if (seen.has(number)) error = "twice";
      else seen.set(number, i + 1);
    }
    rows.push({ line: i + 1, number, ...name, error });
  });
  return rows;
}

/** The rows without errors as CSV for the squad import (Nr;Vorname;Nachname, quoted). */
export function quickCsv(rows: readonly QuickRow[]): string {
  const q = (s: string) => `"${s.replace(/"/g, '""')}"`;
  return ["Nr;Vorname;Nachname", ...rows.filter((r) => !r.error).map((r) => [r.number ?? "", q(r.first), q(r.last)].join(";"))].join("\n");
}

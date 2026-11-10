/**
 * Public holidays most Swiss clubs do not train on: the federal holiday, the Christian holidays
 * of nearly all cantons and Berchtoldstag. Cantonal extras (e.g. Fronleichnam) are left to the
 * coach. Dates as YYYY-MM-DD.
 */
export interface Holiday {
  date: string;
  key: "newYear" | "berchtold" | "goodFriday" | "easterMonday" | "ascension" | "whitMonday" | "national" | "christmas" | "stephen";
}

const iso = (d: Date) => d.toISOString().slice(0, 10);
const utc = (y: number, m: number, d: number) => new Date(Date.UTC(y, m - 1, d));
const plus = (d: Date, days: number) => new Date(d.getTime() + days * 86400_000);

/** Easter Sunday (Gregorian, anonymous algorithm). */
export function easter(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return utc(year, month, day);
}

function ofYear(y: number): Holiday[] {
  const e = easter(y);
  return [
    { date: iso(utc(y, 1, 1)), key: "newYear" },
    { date: iso(utc(y, 1, 2)), key: "berchtold" },
    { date: iso(plus(e, -2)), key: "goodFriday" },
    { date: iso(plus(e, 1)), key: "easterMonday" },
    { date: iso(plus(e, 39)), key: "ascension" },
    { date: iso(plus(e, 50)), key: "whitMonday" },
    { date: iso(utc(y, 8, 1)), key: "national" },
    { date: iso(utc(y, 12, 25)), key: "christmas" },
    { date: iso(utc(y, 12, 26)), key: "stephen" },
  ];
}

/** The holidays between two days (inclusive), in order. */
export function holidaysBetween(from: string, to: string): Holiday[] {
  const out: Holiday[] = [];
  for (let y = Number(from.slice(0, 4)); y <= Number(to.slice(0, 4)); y++) out.push(...ofYear(y));
  return out.filter((h) => h.date >= from && h.date <= to).sort((a, b) => a.date.localeCompare(b.date));
}

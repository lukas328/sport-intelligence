/**
 * Date and time as the coach writes them in Switzerland (L16): «16.11.2026» and «14:30», 24 hours,
 * whatever language the browser is set to (a native date field shows «11/16/2026, 02:23 PM» in an
 * English browser). Parsing is lenient: «16.11.26», «16.11.», «1630», «16.30» are understood.
 */

const pad = (n: number) => String(n).padStart(2, "0");

export function formatDate(d: Date): string {
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

export function formatTime(d: Date): string {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** «16.11.2026», «16.11.26», «16.11.» (this year), «2026-11-16»: [year, month, day] or null. */
export function parseDate(text: string, today = new Date()): [number, number, number] | null {
  const v = text.trim();
  let y: number;
  let m: number;
  let d: number;
  const iso = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(v);
  const ch = /^(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2}|\d{4})?)?\.?$/.exec(v);
  if (iso) {
    [y, m, d] = [Number(iso[1]), Number(iso[2]), Number(iso[3])];
  } else if (ch) {
    d = Number(ch[1]);
    m = Number(ch[2]);
    y = ch[3] ? Number(ch[3]) : today.getFullYear();
    if (y < 100) y += 2000;
  } else {
    return null;
  }
  const check = new Date(y, m - 1, d);
  if (check.getFullYear() !== y || check.getMonth() !== m - 1 || check.getDate() !== d) return null;
  return [y, m, d];
}

/** «14:30», «14.30», «1430», «9» (9:00): [hours, minutes] or null. */
export function parseTime(text: string): [number, number] | null {
  const v = text.trim().replace(/\s*(uhr|h)$/i, "");
  const m = /^(\d{1,2})(?:[:.h]?(\d{2}))?$/.exec(v);
  if (!m) return null;
  const h = Number(m[1]);
  const min = m[2] ? Number(m[2]) : 0;
  if (h > 23 || min > 59) return null;
  return [h, min];
}

/** The local moment of a date and a time, or null when one of them is not understood. */
export function combine(date: string, time: string, today = new Date()): Date | null {
  const d = parseDate(date, today);
  const t = parseTime(time);
  if (!d || !t) return null;
  return new Date(d[0], d[1] - 1, d[2], t[0], t[1]);
}

/** «2026-11-16» for a native date picker from a written date (empty when not understood). */
export function isoDay(text: string): string {
  const d = parseDate(text);
  return d ? `${d[0]}-${pad(d[1])}-${pad(d[2])}` : "";
}

/**
 * What the kick-off field of a new match proposes. Not the minute of the click (at night that was
 * «00:57»). A coach creates a match by hand mostly to upload the video of one just played (future
 * matches come from the schedule of handball.ch), so the proposal lies in the past, where the
 * match page opens on the upload: during the day the last full hour, at night and early in the
 * morning (before nine) last evening at 18:00. The fields stay editable and required.
 */
export function defaultKickoff(now = new Date()): { day: string; clock: string } {
  if (now.getHours() < 9) return { day: formatDate(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)), clock: "18:00" };
  return { day: formatDate(now), clock: `${pad(now.getHours())}:00` };
}

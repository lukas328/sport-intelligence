export function formatClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m);
  return `${h > 0 ? `${h}:` : ""}${mm}:${String(s).padStart(2, "0")}`;
}

export function formatBytes(bytes: number, locale = "de-CH"): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = bytes;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: i >= 3 ? 2 : 0 }).format(v)} ${units[i]}`;
}

export interface ThumbCue {
  start: number;
  end: number;
  url: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Parses a WebVTT thumbnail track ("thumbs.jpg#xywh=0,0,160,90"). */
export function parseThumbVtt(text: string, base: string): ThumbCue[] {
  const toS = (t: string) => {
    const parts = t.trim().split(":").map(Number);
    return parts.reduce((acc, p) => acc * 60 + p, 0);
  };
  const cues: ThumbCue[] = [];
  const blocks = text.split(/\r?\n\r?\n/);
  for (const block of blocks) {
    const lines = block.trim().split(/\r?\n/);
    const timing = lines.find((l) => l.includes("-->"));
    const target = lines[lines.indexOf(timing ?? "") + 1];
    if (!timing || !target) continue;
    const [a, b] = timing.split("-->");
    const m = /^(.*)#xywh=(\d+),(\d+),(\d+),(\d+)$/.exec(target.trim());
    if (!m || !a || !b) continue;
    cues.push({ start: toS(a), end: toS(b), url: `${base}${m[1]}`, x: +m[2]!, y: +m[3]!, w: +m[4]!, h: +m[5]! });
  }
  return cues;
}

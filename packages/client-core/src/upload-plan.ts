/**
 * Resumable multipart upload plan (addendum 01, 5.2): the phone uploads the recording in parts,
 * preferably on Wi-Fi, and continues after a lost connection with the parts still missing.
 */
export interface Part {
  number: number; // 1-based, as in S3 multipart uploads
  start: number; // byte offset, inclusive
  end: number; // byte offset, exclusive
}

export const MIB = 1024 * 1024;

export function planParts(size: number, partSize = 16 * MIB): Part[] {
  if (size <= 0) return [];
  const parts: Part[] = [];
  for (let start = 0, n = 1; start < size; start += partSize, n++) {
    parts.push({ number: n, start, end: Math.min(size, start + partSize) });
  }
  return parts;
}

export function missing(parts: Part[], done: Iterable<number>): Part[] {
  const finished = new Set(done);
  return parts.filter((p) => !finished.has(p.number));
}

export type Network = "wifi" | "cellular" | "none" | "unknown";

/** Upload now? Large uploads wait for Wi-Fi unless the user allowed mobile data. */
export function mayUpload(network: Network, bytesLeft: number, allowCellular: boolean, cellularLimit = 200 * MIB): boolean {
  if (network === "none") return false;
  if (network === "wifi" || network === "unknown") return true;
  return allowCellular || bytesLeft <= cellularLimit;
}

export function progress(parts: Part[], done: Iterable<number>): number {
  const total = parts.reduce((s, p) => s + (p.end - p.start), 0);
  if (total === 0) return 1;
  const finished = new Set(done);
  const sent = parts.filter((p) => finished.has(p.number)).reduce((s, p) => s + (p.end - p.start), 0);
  return sent / total;
}

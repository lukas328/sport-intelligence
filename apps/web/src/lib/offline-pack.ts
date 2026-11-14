/**
 * Packs a presentation for offline use (addendum 01, 4.1): the presentation data, the presenter page
 * and only the HLS segments inside the clip windows (lowest rendition) go into the cache
 * "hb-pres-<id>"; the service worker serves them when the hall has no network.
 */

export interface PackClip {
  video_id: string;
  in_ms: number;
  out_ms: number;
}

export interface Segment {
  uri: string;
  start: number;
  end: number;
  /** the init segment of the file this segment belongs to (a joined playlist has one per file) */
  init?: string | null;
}

/** Segments of a media playlist with their time range in seconds, plus the init segment. */
export function parseMediaPlaylist(text: string): { init: string | null; segments: Segment[] } {
  let t = 0;
  let dur = 0;
  let init: string | null = null;
  const segments: Segment[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    // a match in several files: each file after a discontinuity has its own init segment
    if (line.startsWith("#EXT-X-MAP:")) init = /URI="([^"]+)"/.exec(line)?.[1] ?? null;
    else if (line.startsWith("#EXTINF:")) dur = parseFloat(line.slice(8));
    else if (line && !line.startsWith("#")) {
      segments.push({ uri: line, start: t, end: t + dur, init });
      t += dur;
    }
  }
  return { init: segments[0]?.init ?? init, segments };
}

/** The variant with the lowest bandwidth (smallest download for the cabin laptop). */
export function lowestVariant(master: string): string | null {
  let best: { bw: number; uri: string } | null = null;
  const lines = master.split(/\r?\n/);
  lines.forEach((line, i) => {
    if (!line.startsWith("#EXT-X-STREAM-INF")) return;
    const bw = Number(/BANDWIDTH=(\d+)/.exec(line)?.[1] ?? Infinity);
    const uri = lines[i + 1]?.trim();
    if (uri && (!best || bw < best.bw)) best = { bw, uri };
  });
  return (best as { uri: string } | null)?.uri ?? null;
}

export function cacheName(presId: string): string {
  return `hb-pres-${presId}`;
}

export async function packPresentation(
  orgId: string,
  presId: string,
  clips: PackClip[],
  extra: string[],
  onProgress?: (done: number, total: number) => void,
): Promise<number> {
  const cache = await caches.open(cacheName(presId));
  const urls = new Set<string>([`/v1/orgs/${orgId}/presentations/${presId}`, `/app/${orgId}/presentations/${presId}/present`, ...extra]);
  for (const c of clips) {
    const base = `/v1/orgs/${orgId}/videos/${c.video_id}/media/hls/`;
    const master = await (await fetch(`${base}master.m3u8`)).text();
    urls.add(`${base}master.m3u8`);
    const variant = lowestVariant(master);
    if (!variant) continue;
    const playlistUrl = new URL(variant, location.origin + base).pathname;
    const { init, segments } = parseMediaPlaylist(await (await fetch(playlistUrl)).text());
    urls.add(playlistUrl);
    const dir = playlistUrl.slice(0, playlistUrl.lastIndexOf("/") + 1);
    // the cache is asked with the URL the player resolves: "../" of a joined playlist resolved
    const at = (uri: string) => new URL(uri, location.origin + dir).pathname;
    if (init) urls.add(at(init));
    for (const s of segments)
      if (s.end > c.in_ms / 1000 && s.start < c.out_ms / 1000) {
        urls.add(at(s.uri));
        if (s.init) urls.add(at(s.init));
      }
  }
  const list = [...urls];
  let done = 0;
  for (const u of list) {
    const res = await fetch(u, { credentials: "same-origin" });
    if (res.ok) await cache.put(u, res);
    onProgress?.(++done, list.length);
  }
  return list.length;
}

export async function isPacked(presId: string): Promise<boolean> {
  return typeof caches !== "undefined" && (await caches.keys()).includes(cacheName(presId));
}

export async function unpack(presId: string): Promise<void> {
  await caches.delete(cacheName(presId));
}

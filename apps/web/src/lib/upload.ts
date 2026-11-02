/**
 * Resumable direct-to-storage upload (S3 multipart with presigned part URLs, BRIEF 6.2).
 *
 * The browser asks the API for part URLs, PUTs file slices straight to storage (4 in parallel),
 * and finally tells the API which parts (ETags) make up the file. The upload id is remembered per
 * file fingerprint, so after a closed tab, crash or lost connection the same file continues where it
 * stopped: the API lists the parts that already arrived.
 */

export interface UploadApi {
  create(input: { filename: string; size_bytes: number; content_type: string; role: string }): Promise<{
    videoId: string;
    partSize: number;
    partCount: number;
  }>;
  listParts(videoId: string): Promise<{ number: number; etag: string; size: number }[]>;
  presign(videoId: string, numbers: number[]): Promise<{ number: number; url: string }[]>;
  complete(videoId: string, parts: { number: number; etag: string }[]): Promise<void>;
}

export interface StoredUpload {
  videoId: string;
  partSize: number;
  partCount: number;
}

export interface Store {
  get(key: string): StoredUpload | null;
  set(key: string, value: StoredUpload): void;
  remove(key: string): void;
}

export interface UploadOptions {
  api: UploadApi;
  store: Store;
  putPart: (url: string, body: Blob, signal: AbortSignal) => Promise<string>; // returns ETag
  concurrency?: number;
  retries?: number;
  onProgress?: (uploadedBytes: number, totalBytes: number) => void;
  signal?: AbortSignal;
  scope: string; // e.g. match id + role, so the same file can go to different matches
}

export function fingerprint(file: { name: string; size: number; lastModified: number }, scope: string): string {
  return `hb-upload:${scope}:${file.name}:${file.size}:${file.lastModified}`;
}

export class UploadAbortedError extends Error {
  constructor() {
    super("upload aborted");
  }
}

export async function uploadFile(file: File, role: string, opts: UploadOptions): Promise<{ videoId: string; resumed: boolean }> {
  const { api, store, putPart, concurrency = 4, retries = 3, onProgress, signal } = opts;
  const key = fingerprint(file, opts.scope);
  let state = store.get(key);
  let done = new Map<number, { etag: string; size: number }>();
  let resumed = false;
  if (state) {
    try {
      for (const p of await api.listParts(state.videoId)) done.set(p.number, { etag: p.etag, size: p.size });
      resumed = true;
    } catch {
      store.remove(key); // expired or already finished: start over
      state = null;
      done = new Map();
    }
  }
  if (!state) {
    const created = await api.create({
      filename: file.name,
      size_bytes: file.size,
      content_type: file.type && file.type.startsWith("video/") ? file.type : "video/mp4",
      role,
    });
    state = { videoId: created.videoId, partSize: created.partSize, partCount: created.partCount };
    store.set(key, state);
  }
  const { videoId, partSize, partCount } = state;
  const expected = (n: number) => Math.min(partSize, file.size - (n - 1) * partSize);
  // a part that arrived only partially is uploaded again
  for (const [n, p] of done) if (p.size !== expected(n)) done.delete(n);

  let uploaded = [...done.entries()].reduce((sum, [, p]) => sum + p.size, 0);
  onProgress?.(uploaded, file.size);
  const pending = Array.from({ length: partCount }, (_, i) => i + 1).filter((n) => !done.has(n));

  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort);
  try {
    const urls = new Map<number, string>();
    const fetchUrls = async (numbers: number[]) => {
      for (let i = 0; i < numbers.length; i += 50) {
        for (const u of await api.presign(videoId, numbers.slice(i, i + 50))) urls.set(u.number, u.url);
      }
    };
    let cursor = 0;
    const worker = async () => {
      while (cursor < pending.length) {
        if (controller.signal.aborted) throw new UploadAbortedError();
        const n = pending[cursor++]!;
        if (!urls.has(n)) await fetchUrls(pending.slice(cursor - 1, cursor + 49).filter((x) => !urls.has(x)));
        const blob = file.slice((n - 1) * partSize, Math.min(n * partSize, file.size));
        let attempt = 0;
        for (;;) {
          try {
            const etag = await putPart(urls.get(n)!, blob, controller.signal);
            done.set(n, { etag, size: blob.size });
            uploaded += blob.size;
            onProgress?.(uploaded, file.size);
            break;
          } catch (e) {
            if (controller.signal.aborted) throw new UploadAbortedError();
            if (++attempt > retries) throw e;
            await new Promise((r) => setTimeout(r, 500 * 2 ** attempt));
            await fetchUrls([n]); // URL may have expired
          }
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(concurrency, pending.length) }, worker));
    await api.complete(
      videoId,
      [...done.entries()].sort(([a], [b]) => a - b).map(([number, p]) => ({ number, etag: p.etag })),
    );
    store.remove(key);
    return { videoId, resumed };
  } finally {
    signal?.removeEventListener("abort", abort);
  }
}

/** PUT a part with XHR (fetch has no upload progress and hides ETag without CORS expose). */
export function xhrPutPart(url: string, body: Blob, signal: AbortSignal): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.onload = () => {
      const etag = xhr.getResponseHeader("ETag");
      if (xhr.status >= 200 && xhr.status < 300 && etag) resolve(etag.replaceAll('"', ""));
      else reject(new Error(`part upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("network error"));
    signal.addEventListener("abort", () => xhr.abort());
    xhr.onabort = () => reject(new UploadAbortedError());
    xhr.send(body);
  });
}

export const localStore: Store = {
  get(key) {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as StoredUpload) : null;
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* private mode: resume not available */
    }
  },
  remove(key) {
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  },
};

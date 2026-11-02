import { describe, expect, it, vi } from "vitest";
import { fingerprint, uploadFile, UploadAbortedError, type Store, type StoredUpload, type UploadApi } from "./upload";

function memoryStore(): Store & { data: Map<string, StoredUpload> } {
  const data = new Map<string, StoredUpload>();
  return { data, get: (k) => data.get(k) ?? null, set: (k, v) => void data.set(k, v), remove: (k) => void data.delete(k) };
}

class FakeStorage {
  parts = new Map<number, number>(); // number -> size
  completed: { number: number; etag: string }[] | null = null;
  failOnce = new Set<number>();
  api(partSize: number, partCount: number): UploadApi {
    return {
      create: vi.fn(async () => ({ videoId: "v1", partSize, partCount })),
      listParts: vi.fn(async () => [...this.parts].map(([number, size]) => ({ number, etag: `e${number}`, size }))),
      presign: vi.fn(async (_id: string, numbers: number[]) => numbers.map((n) => ({ number: n, url: `u${n}` }))),
      complete: vi.fn(async (_id: string, parts: { number: number; etag: string }[]) => {
        this.completed = parts;
      }),
    };
  }
  put = async (url: string, body: Blob) => {
    const n = Number(url.slice(1));
    if (this.failOnce.delete(n)) throw new Error("flaky");
    this.parts.set(n, body.size);
    return `e${n}`;
  };
}

const file = (size: number) => new File([new Uint8Array(size)], "spiel.mp4", { type: "video/mp4", lastModified: 1 });

describe("uploadFile", () => {
  it("uploads all parts and completes in order", async () => {
    const s = new FakeStorage();
    const store = memoryStore();
    const progress: number[] = [];
    const res = await uploadFile(file(25), "main", {
      api: s.api(10, 3), store, putPart: s.put, scope: "m1", onProgress: (u) => progress.push(u),
    });
    expect(res).toEqual({ videoId: "v1", resumed: false });
    expect(s.completed).toEqual([1, 2, 3].map((n) => ({ number: n, etag: `e${n}` })));
    expect(progress.at(-1)).toBe(25);
    expect(store.data.size).toBe(0);
  });

  it("resumes after an abort without uploading finished parts again", async () => {
    const s = new FakeStorage();
    const store = memoryStore();
    const f = file(25);
    const ctrl = new AbortController();
    const api = s.api(10, 3);
    let calls = 0;
    const put = async (url: string, body: Blob) => {
      if (++calls === 2) ctrl.abort();
      return s.put(url, body);
    };
    await expect(uploadFile(f, "main", { api, store, putPart: put, scope: "m1", concurrency: 1, signal: ctrl.signal }))
      .rejects.toBeInstanceOf(UploadAbortedError);
    expect(store.get(fingerprint(f, "m1"))?.videoId).toBe("v1");
    const before = new Map(s.parts);
    const spy = vi.fn(s.put);
    const res = await uploadFile(f, "main", { api, store, putPart: spy, scope: "m1" });
    expect(res.resumed).toBe(true);
    expect(api.create).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledTimes(3 - before.size);
    expect(s.completed?.map((p) => p.number)).toEqual([1, 2, 3]);
  });

  it("re-uploads a partially stored part and retries flaky parts", async () => {
    const s = new FakeStorage();
    s.parts.set(1, 10);
    s.parts.set(2, 4); // truncated
    s.failOnce.add(3);
    const store = memoryStore();
    const f = file(25);
    store.set(fingerprint(f, "m1"), { videoId: "v1", partSize: 10, partCount: 3 });
    const spy = vi.fn(s.put);
    await uploadFile(f, "main", { api: s.api(10, 3), store, putPart: spy, scope: "m1", retries: 2 });
    expect(spy.mock.calls.map((c) => c[0])).toEqual(expect.arrayContaining(["u2", "u3"]));
    expect(spy).not.toHaveBeenCalledWith("u1", expect.anything(), expect.anything());
    expect(s.parts.get(2)).toBe(10);
  });

  it("starts over when the stored upload expired", async () => {
    const s = new FakeStorage();
    const store = memoryStore();
    const f = file(5);
    store.set(fingerprint(f, "m1"), { videoId: "old", partSize: 10, partCount: 1 });
    const api = s.api(10, 1);
    api.listParts = vi.fn(async () => {
      throw new Error("410");
    });
    const res = await uploadFile(f, "main", { api, store, putPart: s.put, scope: "m1" });
    expect(res).toEqual({ videoId: "v1", resumed: false });
  });
});

import { describe, expect, it } from "vitest";
import { flush, mark, pending } from "./marks-queue";

function memory() {
  const data = new Map<string, string>();
  return { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v) };
}

describe("marks queue", () => {
  it("keeps the phone time and sends in one batch", async () => {
    const s = memory();
    mark(s, "m1", "goal_own", new Date("2026-11-07T18:10:00Z"), "a");
    mark(s, "m1", "press", new Date("2026-11-07T18:11:00Z"), "b");
    expect(pending(s, "m1").map((m) => m.device_time)).toEqual(["2026-11-07T18:10:00.000Z", "2026-11-07T18:11:00.000Z"]);
    const sent: string[][] = [];
    const left = await flush(s, "m1", async (items) => {
      sent.push(items.map((i) => i.client_id));
      return { ok: true, stored: ["a", "b"] };
    });
    expect(left).toBe(0);
    expect(sent).toEqual([["a", "b"]]);
  });

  it("keeps marks when offline or rejected", async () => {
    const s = memory();
    mark(s, "m1", "goal_opp", new Date(), "x");
    expect(await flush(s, "m1", async () => { throw new Error("offline"); })).toBe(1);
    expect(await flush(s, "m1", async () => ({ ok: false }))).toBe(1);
    expect(pending(s, "m1")).toHaveLength(1);
    expect(await flush(s, "other", async () => ({ ok: true }))).toBe(0);
  });
});

describe("taking a mark back", () => {
  it("removes a queued mark before it goes out (UX test N14)", async () => {
    const { forget } = await import("./marks-queue");
    const data: Record<string, string> = {};
    const store = { getItem: (k: string) => data[k] ?? null, setItem: (k: string, v: string) => void (data[k] = v) };
    const a = mark(store, "m1", "good");
    mark(store, "m1", "goal_own");
    expect(forget(store, "m1", a.client_id)).toBe(true);
    expect(pending(store, "m1").map((x) => x.key)).toEqual(["goal_own"]);
    expect(forget(store, "m1", a.client_id)).toBe(false);
  });
});

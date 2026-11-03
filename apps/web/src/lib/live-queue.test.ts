import { describe, expect, it } from "vitest";
import { adjust, clockSeconds, enqueue, flush, load, remove, toggle } from "./live-queue";

function memory() {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) };
}

describe("live queue", () => {
  it("keeps events per match with a client id", () => {
    const s = memory();
    const a = enqueue(s, "m1", { type: "shot" }, "id-a");
    enqueue(s, "m2", { type: "shot" }, "id-b");
    expect(a.body.client_id).toBe("id-a");
    expect(load(s, "m1").map((e) => e.client_id)).toEqual(["id-a"]);
    remove(s, "m1", "id-a");
    expect(load(s, "m1")).toEqual([]);
    expect(load({ getItem: () => "{broken", setItem: () => undefined }, "x")).toEqual([]);
  });

  it("flushes in order, stops when offline, drops invalid events", async () => {
    const s = memory();
    for (const id of ["1", "2", "3", "4"]) enqueue(s, "m", { n: id }, id);
    const calls: unknown[] = [];
    let offline = false;
    const post = async (body: Record<string, unknown>) => {
      calls.push(body.n);
      if (offline) throw new TypeError("network");
      if (body.n === "2") return { ok: false, status: 422 };
      if (body.n === "3") {
        offline = true;
        throw new TypeError("network");
      }
      return { ok: true, status: 201, id: `srv-${String(body.n)}` };
    };
    const r = await flush(s, "m", post);
    expect(calls).toEqual(["1", "2", "3"]);
    expect(r.sent).toEqual([{ client_id: "1", id: "srv-1" }]);
    expect(r.rejected.map((e) => e.client_id)).toEqual(["2"]);
    expect(r.pending).toBe(2);
    offline = false;
    const again = await flush(s, "m", async () => ({ ok: true, status: 201 }));
    expect(again.sent.map((e) => e.client_id)).toEqual(["3", "4"]);
    expect(again.pending).toBe(0);
    enqueue(s, "m", {}, "5");
    expect((await flush(s, "m", async () => ({ ok: false, status: 503 }))).pending).toBe(1);
  });

  it("runs a match clock that survives reloads", () => {
    let c = { period: 1, base_s: 0, started_at: null as number | null };
    c = toggle(c, 1000);
    expect(clockSeconds(c, 61_000)).toBe(60);
    c = toggle(c, 61_000);
    expect(c).toEqual({ period: 1, base_s: 60, started_at: null });
    expect(clockSeconds(c, 999_999)).toBe(60);
    expect(clockSeconds(adjust(c, -100))).toBe(0);
    expect(clockSeconds(adjust(toggle(c, 0), 10, 0), 5000)).toBe(75);
  });
});

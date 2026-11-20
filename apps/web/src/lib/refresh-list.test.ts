import { QueryClient, QueryObserver } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { refreshList } from "./refresh-list";

/** A list on the "server" and a first load the test lets finish when it wants. */
function setup() {
  const server = ["Montag"];
  const held: Array<() => void> = [];
  let calls = 0;
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const key = ["sessions", "t1"];
  const observer = new QueryObserver(qc, {
    queryKey: key,
    queryFn: () => {
      calls += 1;
      const snapshot = [...server];
      // the first load is slow (dev server): it answers with what the server had when it started
      if (calls === 1) return new Promise<string[]>((resolve) => held.push(() => resolve(snapshot)));
      return Promise.resolve(snapshot);
    },
  });
  const stop = observer.subscribe(() => {});
  return { qc, key, server, held, calls: () => calls, observer, stop };
}

describe("refreshList", () => {
  it("a plain invalidate joins the slow first load and misses the new entry", async () => {
    const s = setup();
    s.server.push("Neu");
    const done = s.qc.invalidateQueries({ queryKey: s.key });
    s.held.forEach((f) => f());
    await done;
    expect(s.calls()).toBe(1);
    expect(s.qc.getQueryData(s.key)).toEqual(["Montag"]);
    s.stop();
  });

  it("loads the list again after the write, even while the first load still runs", async () => {
    const s = setup();
    s.server.push("Neu");
    const done = refreshList(s.qc, s.key);
    s.held.forEach((f) => f());
    await done;
    expect(s.calls()).toBe(2);
    expect(s.qc.getQueryData(s.key)).toEqual(["Montag", "Neu"]);
    s.stop();
  });

  it("refetches a list that is already loaded", async () => {
    const s = setup();
    s.held.forEach((f) => f());
    await s.observer.refetch();
    s.server.push("Neu");
    await refreshList(s.qc, s.key);
    expect(s.qc.getQueryData(s.key)).toEqual(["Montag", "Neu"]);
    s.stop();
  });
});

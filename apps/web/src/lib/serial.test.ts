import { describe, expect, it } from "vitest";
import { serial } from "./serial";

function gate() {
  let open!: () => void;
  const p = new Promise<void>((r) => (open = r));
  return { p, open };
}

describe("serial", () => {
  it("runs once more for a call during a run, never twice at the same time", async () => {
    let runs = 0;
    let parallel = 0;
    let most = 0;
    const gates = [gate(), gate()];
    const run = serial(async () => {
      parallel++;
      most = Math.max(most, parallel);
      await gates[runs++]!.p;
      parallel--;
    });
    const first = run();
    const second = run();
    const third = run();
    expect(second).toBe(first);
    expect(third).toBe(first);
    gates[0]!.open();
    gates[1]!.open();
    await first;
    expect(runs).toBe(2);
    expect(most).toBe(1);
  });
  it("runs once without a call in between, and again on the next call", async () => {
    let runs = 0;
    const run = serial(async () => void runs++);
    await run();
    expect(runs).toBe(1);
    await run();
    expect(runs).toBe(2);
  });
  it("keeps working after a failed run", async () => {
    let runs = 0;
    const run = serial(async () => {
      runs++;
      if (runs === 1) throw new Error("offline");
    });
    await expect(run()).rejects.toThrow("offline");
    await run();
    expect(runs).toBe(2);
  });
});

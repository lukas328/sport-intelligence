import { describe, expect, it } from "vitest";
import { CLICKS_PER_LINE, countOn, flowReducer, initialFlow, offeredLine, type FlowAction, type FlowState } from "./calibration-flow";
import { equations, fitClicks, type Pt } from "./court-fit";
import { HALL_H, HALL_SIZE, project } from "./synthetic-hall";

const run = (s: FlowState, ...actions: FlowAction[]) => actions.reduce(flowReducer, s);
const at = (x: number, y: number): Pt => project(HALL_H, x, y);

describe("calibration dialog flow", () => {
  it("starts with the suggestion when there is one, else with the lines", () => {
    expect(initialFlow({ suggestion: true }).step).toBe("suggest");
    expect(initialFlow({ suggestion: false }).step).toBe("mark");
    // the coach's last clicks: straight to them, the next line without clicks chosen
    const again = initialFlow({ suggestion: true, clicks: { points: {}, lines: { side_near: [at(5, 0), at(30, 0)] } } });
    expect(again.step).toBe("mark");
    expect(again.line).toBe("side_far");
    expect(countOn(again.clicks, "side_near")).toBe(2);
  });

  it("ignores taps on the picture before «Korrigieren»", () => {
    const s = run(initialFlow({ suggestion: true }), { type: "place", p: [10, 10] });
    expect(equations(s.clicks)).toBe(0);
    expect(run(s, { type: "correct" }).step).toBe("mark");
  });

  it("offers the next line after three clicks, keeps a fourth on the chosen one, gives a court the server takes", () => {
    let s = initialFlow({ suggestion: false });
    for (const x of [5, 18]) s = run(s, { type: "place", p: at(x, 0) });
    expect(offeredLine(s)).toBeNull();
    s = run(s, { type: "place", p: at(33, 0) });
    // three clicks: the next line is offered, the chosen one stays (no silent switch)
    expect(s.line).toBe("side_near");
    expect(offeredLine(s)).toBe("side_far");
    s = run(s, { type: "place", p: at(26, 0) });
    expect(s.clicks.lines.side_near).toHaveLength(4);
    s = run(s, { type: "line", name: offeredLine(s)! });
    for (const x of [7, 20, 32]) s = run(s, { type: "place", p: at(x, 20) });
    expect(offeredLine(s)).toBe("goal_left");
    s = run(s, { type: "line", name: "goal_left" });
    s = run(s, { type: "place", p: at(0, 4) }, { type: "place", p: at(0, 15) });
    // two clicks: the line stays chosen until the coach picks another
    expect(s.line).toBe("goal_left");
    s = run(s, { type: "line", name: "centre" }, { type: "place", p: at(20, 3) }, { type: "place", p: at(20, 17) });
    expect(equations(s.clicks)).toBe(11);
    expect(CLICKS_PER_LINE).toBe(3);
    const fit = fitClicks(s.clicks, HALL_SIZE);
    expect(fit.status).toBe("ok");
    expect(fit.medianPx!).toBeLessThan(0.1);
  });

  it("undoes clicks, a drag and a cleared line, one step at a time", () => {
    let s = run(initialFlow({ suggestion: false }), { type: "place", p: [100, 600] }, { type: "place", p: [400, 610] });
    s = run(s, { type: "move", ref: { kind: "line", name: "side_near", index: 1 }, p: [420, 612], prev: [400, 610] });
    expect(s.clicks.lines.side_near![1]).toEqual([420, 612]);
    s = run(s, { type: "clearLine", name: "side_near" });
    expect(s.clicks.lines.side_near).toBeUndefined();
    s = run(s, { type: "undo" });
    expect(s.clicks.lines.side_near).toHaveLength(2);
    s = run(s, { type: "undo" });
    expect(s.clicks.lines.side_near![1]).toEqual([400, 610]);
    s = run(s, { type: "undo" }, { type: "undo" });
    expect(s.clicks.lines.side_near).toBeUndefined();
    expect(run(s, { type: "undo" })).toBe(s);
  });

  it("nudges the last click with the keys, a run of nudges is one step back", () => {
    let s = run(initialFlow({ suggestion: false }), { type: "place", p: [100, 600] });
    s = run(s, { type: "nudge", dx: 0.5, dy: 0 }, { type: "nudge", dx: 0.5, dy: 0 }, { type: "nudge", dx: 0, dy: -5 });
    expect(s.clicks.lines.side_near![0]).toEqual([101, 595]);
    s = run(s, { type: "undo" });
    expect(s.clicks.lines.side_near![0]).toEqual([100, 600]);
  });

  it("sets named points in the advanced mode and moves on to the next free point", () => {
    let s = run(initialFlow({ suggestion: false }), { type: "mode", mode: "point" });
    s = run(s, { type: "point", name: "corner_bl" }, { type: "place", p: at(0, 0) });
    expect(s.clicks.points.corner_bl).toEqual(at(0, 0));
    expect(s.point).toBe("corner_tl");
    // a point set again replaces it; undo brings the first back
    s = run(s, { type: "point", name: "corner_bl" }, { type: "place", p: [1, 1] }, { type: "undo" });
    expect(s.clicks.points.corner_bl).toEqual(at(0, 0));
  });

  it("clears everything and brings it back", () => {
    let s = run(initialFlow({ suggestion: false }), { type: "place", p: [1, 2] }, { type: "line", name: "centre" }, { type: "place", p: [3, 4] });
    s = run(s, { type: "clearAll" });
    expect(equations(s.clicks)).toBe(0);
    expect(equations(run(s, { type: "undo" }).clicks)).toBe(2);
  });
});

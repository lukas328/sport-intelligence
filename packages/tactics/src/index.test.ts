import { describe, expect, it } from "vitest";
import { LIMITS, TACTICS_FORMAT_VERSION, TEMPLATES, clampToCourt, frameFromPositions, nextFrame, searchTemplates, stateAt, totalDuration, validate, type PlayDoc } from "./index";

const two: PlayDoc = {
  formatVersion: TACTICS_FORMAT_VERSION,
  court: "half",
  frames: [
    { tokens: [{ id: "a", side: "own", label: "RM", x: 20, y: 10 }, { id: "b", side: "opp", label: "1", x: 30, y: 10 }], ball: { x: 20, y: 10 }, arrows: [], note: "", duration_ms: 1000 },
    { tokens: [{ id: "a", side: "own", label: "RM", x: 30, y: 12 }], ball: { x: 30, y: 12 }, arrows: [], note: "", duration_ms: 1000 },
  ],
};

describe("tactics", () => {
  it("animates between frames with a hold", () => {
    expect(totalDuration(two)).toBe(2000);
    expect(stateAt(two, 0).tokens[0]).toMatchObject({ x: 20, y: 10 });
    expect(stateAt(two, 250).tokens[0]).toMatchObject({ x: 20, y: 10 }); // hold phase
    const mid = stateAt(two, 650).tokens[0]!;
    expect(mid.x).toBeGreaterThan(24);
    expect(mid.x).toBeLessThan(26);
    expect(stateAt(two, 1000).tokens[0]).toMatchObject({ x: 30, y: 12 });
    expect(stateAt(two, 1500)).toMatchObject({ frame: 1, ball: { x: 30, y: 12 } });
    expect(stateAt(two, 99_999).frame).toBe(1);
    expect(stateAt(two, 650).tokens).toHaveLength(2); // b stays until its frame ends
    expect(stateAt({ ...two, frames: [] }, 0).tokens).toEqual([]);
  });

  it("next frame follows run arrows and passes", () => {
    const f = { ...two.frames[0]!, arrows: [{ kind: "run" as const, points: [[20, 10], [25, 5]] as [number, number][] }, { kind: "pass" as const, points: [[20, 10], [30, 10]] as [number, number][] }] };
    const n = nextFrame(f);
    expect(n.tokens[0]).toMatchObject({ x: 25, y: 5 });
    expect(n.tokens[1]).toMatchObject({ x: 30, y: 10 });
    expect(n.ball).toEqual({ x: 30, y: 10 });
    expect(n.arrows).toEqual([]);
    expect(nextFrame({ ...two.frames[0]!, ball: null }).ball).toBeNull();
  });

  it("validates limits", () => {
    expect(validate(two)).toEqual([]);
    const bad: PlayDoc = { ...two, frames: [{ ...two.frames[0]!, duration_ms: 50, tokens: [two.frames[0]!.tokens[0]!, two.frames[0]!.tokens[0]!], arrows: [{ kind: "run", points: [[0, 0]] }], note: "x".repeat(LIMITS.note + 1) }] };
    expect(validate(bad)).toEqual(["frame 0: duplicate token", "frame 0: arrow points", "frame 0: note", "frame 0: duration"]);
    expect(validate({ ...two, frames: [] })).toEqual(["frames"]);
  });

  it("templates are valid and searchable", () => {
    for (const t of TEMPLATES) expect(validate(t.doc), t.id).toEqual([]);
    expect(searchTemplates("5-1").map((t) => t.id)).toEqual(["def_5_1"]);
    expect(searchTemplates("sperre").map((t) => t.id)).toEqual(["att_pivot_screen"]);
    expect(searchTemplates("", "defence")).toHaveLength(4);
    // every defence template has a goalkeeper and six court players of each team
    for (const t of TEMPLATES.filter((x) => x.category === "defence")) {
      const f = t.doc.frames[0]!;
      expect(f.tokens.filter((k) => k.side === "own")).toHaveLength(7);
      expect(f.tokens.filter((k) => k.side === "opp")).toHaveLength(6);
      for (const k of f.tokens) expect(k.x).toBeGreaterThan(20);
    }
  });

  it("builds a frame from tracking positions", () => {
    const f = frameFromPositions([{ track: 3, side: "own", x: 12.345, y: 3 }, { track: 9, side: "opp", x: 30, y: 10 }]);
    expect(f.tokens).toEqual([
      { id: "o1", side: "own", label: "1", x: 12.35, y: 3 },
      { id: "o2", side: "opp", label: "2", x: 30, y: 10 },
    ]);
    expect(clampToCourt(-5, 30)).toEqual([-1, 21]);
  });
});

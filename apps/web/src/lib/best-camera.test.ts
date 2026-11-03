import { describe, expect, it } from "vitest";
import { bestCamera, cameraAt } from "./best-camera";

const cams = [
  { id: "main", role: "main" },
  { id: "L", role: "goal_cam_left" },
  { id: "R", role: "goal_cam_right" },
];
const shot = (x: number, t: number) => ({ type: "shot", t_ms: t, x, outcome: "save", goal_zone: "TL" });

describe("best camera", () => {
  it("picks the goal camera of the goal shot at", () => {
    expect(bestCamera(shot(8, 0), cams)).toBe("L");
    expect(bestCamera(shot(33, 0), cams)).toBe("R");
    expect(bestCamera({ type: "turnover", t_ms: 0, x: 8, outcome: null, goal_zone: null }, cams)).toBeNull();
    expect(bestCamera(shot(33, 0), cams.slice(0, 2))).toBeNull();
  });
  it("switches only around the event", () => {
    const ev = [shot(33, 60_000)];
    expect(cameraAt(57_000, ev, cams)).toBe("R");
    expect(cameraAt(61_000, ev, cams)).toBe("R");
    expect(cameraAt(50_000, ev, cams)).toBeNull();
  });
});

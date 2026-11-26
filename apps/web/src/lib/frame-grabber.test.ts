import { describe, expect, it } from "vitest";
import { stillRect } from "./frame-grabber";
import { personMoment } from "@/app/app/[orgId]/matches/[matchId]/identity-panel";

describe("stillRect: the part of the frame a person's still shows", () => {
  it("centres the person with room around them, in portrait", () => {
    // a person 10 % of the height tall in the middle of a 1280 x 720 frame
    const r = stillRect({ x: 0.48, y: 0.45, w: 0.04, h: 0.1 }, 1280, 720, 3 / 4);
    expect(r.sh).toBeCloseTo(72 * 1.6);
    expect(r.sw / r.sh).toBeCloseTo(3 / 4);
    expect(r.sx + r.sw / 2).toBeCloseTo(640);
    expect(r.sy + r.sh / 2).toBeCloseTo(360);
  });

  it("stays inside the frame at its edges", () => {
    const corner = stillRect({ x: 0.97, y: 0.9, w: 0.03, h: 0.1 }, 1280, 720);
    expect(corner.sx + corner.sw).toBeLessThanOrEqual(1280);
    expect(corner.sy + corner.sh).toBeLessThanOrEqual(720);
    const left = stillRect({ x: -0.02, y: 0, w: 0.03, h: 0.1 }, 1280, 720);
    expect(left.sx).toBe(0);
    expect(left.sy).toBe(0);
  });

  it("shrinks to the frame for a person close to the camera", () => {
    const r = stillRect({ x: 0.3, y: 0, w: 0.4, h: 1 }, 1280, 720, 3 / 4);
    expect(r.sh).toBeLessThanOrEqual(720);
    expect(r.sw / r.sh).toBeCloseTo(3 / 4);
  });
});

describe("personMoment: when a person is shown", () => {
  it("a little after they appear, never past half their time", () => {
    expect(personMoment({ first_ms: 10_000, last_ms: 60_000 })).toBe(12_000);
    expect(personMoment({ first_ms: 10_000, last_ms: 11_000 })).toBe(10_500);
  });
});

import { describe, expect, it } from "vitest";
import { inView, sceneView, VIEWS } from "@/components/anlauf/geometry";

describe("tactics camera on the side of the video (real-video test G3)", () => {
  it("draws an attack on the goal at x = 40 on the right half, unmirrored", () => {
    expect(sceneView({ right: true }, "camL")).toBe("camR");
    expect(sceneView({ right: true }, "halfB")).toBe("halfBR");
    expect(sceneView({ right: false }, "camL")).toBe("camL");
    // the right half wide: the goal at x = 40 inside the box, positions as they are
    const [x, y, w] = VIEWS.camR.box;
    expect(inView("camR", [40, 10])).toEqual([40, 10]);
    expect(x < 40 && x + w > 40 && y < 0).toBe(true);
  });
  it("turns the right half with its goal at the top, a rotation, not a mirror", () => {
    // the goal at the top, as on the left half
    expect(inView("halfBR", [40, 10])[1]).toBe(0);
    expect(inView("halfB", [0, 10])[1]).toBe(0);
    // the near side line (y = 20, the camera side) of both halves: left half on the right of
    // the turned view, right half on the left: the orientation of a rotation by 180 degrees
    const a = inView("halfBR", [30, 0]);
    const b = inView("halfBR", [30, 20]);
    expect(a[0]).toBeGreaterThan(b[0]);
    expect(a[1]).toBe(b[1]);
  });
});

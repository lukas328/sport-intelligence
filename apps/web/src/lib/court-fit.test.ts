import { describe, expect, it } from "vitest";
import data from "./fixtures/court-clicks.json";
import {
  LINE_NAMES,
  LOCAL_COURT_MODEL,
  MAX_MEDIAN_PX,
  courtAsPoints,
  equations,
  fitClicks,
  linePolylines,
  toCourt,
  type Clicks,
  type Pt,
} from "./court-fit";
import { fitHomography, toImage } from "./court-calibration";

// The clicks of the vision tests (packages/vision/tests/data/court_clicks.json): clicks on
// calibration test set frames (coordinates only, no images) with the homography the reference
// fit gives. Our fit must give the same court where the clicks are.
type Frame = {
  frame: string;
  image_size: [number, number];
  points: Record<string, Pt>;
  lines: Record<string, Pt[]>;
  expected_court_to_image?: number[][];
  expected_median_px?: number;
};
const FRAMES = (data as { frames: Frame[] }).frames;
const SIZE: [number, number] = [1280, 720];

/** Court -> image of a camera beside the near sideline looking at the left goal area. */
const CAMERA = [
  [38, 20, 150],
  [-2, -14, 560],
  [0.004, 0.035, 1],
];

function project(h: number[][], p: Pt): Pt {
  const w = h[2]![0]! * p[0] + h[2]![1]! * p[1] + h[2]![2]!;
  return [(h[0]![0]! * p[0] + h[0]![1]! * p[1] + h[0]![2]!) / w, (h[1]![0]! * p[0] + h[1]![1]! * p[1] + h[1]![2]!) / w];
}

/** Clicks on a court line at fractions of its length (dense polyline like the vision tests). */
function on(h: number[][], name: string, ts: number[]): Pt[] {
  const line = LOCAL_COURT_MODEL.lines[name]!;
  const pl = line.court;
  const lens = pl.slice(1).map((b, i) => Math.hypot(b[0] - pl[i]![0], b[1] - pl[i]![1]));
  const total = lens.reduce((s, v) => s + v, 0);
  return ts.map((t) => {
    let d = t * total;
    for (let i = 0; i < lens.length; i++) {
      if (d <= lens[i]! || i === lens.length - 1) {
        const f = lens[i]! > 0 ? d / lens[i]! : 0;
        const a = pl[i]!;
        const b = pl[i + 1]!;
        return project(h, [a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])]);
      }
      d -= lens[i]!;
    }
    return project(h, pl[pl.length - 1]!);
  });
}

const grid = (xs: number[], ys: number[]) => xs.flatMap((x) => ys.map((y) => [x, y] as Pt));
const maxPx = (a: number[][], b: number[][], pts: Pt[]) => Math.max(...pts.map((p) => Math.hypot(project(a, p)[0] - project(b, p)[0], project(a, p)[1] - project(b, p)[1])));

// a reproducible normal noise
function rng(seed: number) {
  let s = seed;
  const u = () => ((s = (s * 1103515245 + 12345) % 2147483648) + 1) / 2147483649;
  return (sd: number) => sd * Math.sqrt(-2 * Math.log(u())) * Math.cos(2 * Math.PI * u());
}

describe("court fit from clicked lines", () => {
  it("lets the arc fix the court where straight lines leave it open", () => {
    // both sidelines and the goal line fix only 6 of 8 degrees of freedom; the 6 m arc decides
    const clicks: Clicks = {
      points: {},
      lines: {
        side_near: on(CAMERA, "side_near", [0.05, 0.15, 0.3]),
        side_far: on(CAMERA, "side_far", [0.05, 0.2, 0.35]),
        goal_left: on(CAMERA, "goal_left", [0.3, 0.7]),
        six_left: on(CAMERA, "six_left", [0.2, 0.5, 0.8]),
      },
    };
    const fit = fitClicks(clicks, SIZE);
    expect(fit.status).toBe("ok");
    expect(fit.medianPx!).toBeLessThan(0.5);
    expect(maxPx(fit.homography!, CAMERA, grid([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20], [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]))).toBeLessThan(1);
  });

  it("still finds the court from noisy clicks", () => {
    const noise = rng(1);
    const noisy = (ps: Pt[]) => ps.map(([x, y]) => [x + noise(2), y + noise(2)] as Pt);
    const clicks: Clicks = {
      points: {},
      lines: {
        side_near: noisy(on(CAMERA, "side_near", [0.05, 0.15, 0.3])),
        side_far: noisy(on(CAMERA, "side_far", [0.05, 0.2, 0.35])),
        goal_left: noisy(on(CAMERA, "goal_left", [0.3, 0.5, 0.7])),
        six_left: noisy(on(CAMERA, "six_left", [0.2, 0.5, 0.8])),
      },
    };
    const fit = fitClicks(clicks, SIZE);
    expect(fit.status).toBe("ok");
    // court positions near the clicks within a few decimetres
    const back = grid([0, 1, 2, 3, 4, 5, 6, 7, 8], [2, 4, 6, 8, 10, 12, 14, 16, 18]).map((g) => Math.hypot(...(toCourt(fit.homography!, project(CAMERA, g))!.map((v, i) => v - g[i]!) as [number, number])));
    back.sort((a, b) => a - b);
    expect(back[Math.floor(back.length / 2)]!).toBeLessThan(0.3);
  });

  for (const frame of FRAMES.filter((f) => f.expected_court_to_image)) {
    it(`gives the reference court for the clicks of ${frame.frame}`, () => {
      const fit = fitClicks({ points: frame.points, lines: frame.lines }, frame.image_size);
      expect(fit.status).toBe("ok");
      const expected = frame.expected_court_to_image!;
      const clicks = [...Object.values(frame.points), ...Object.values(frame.lines).flat()];
      // compare where both put the court near the clicks (the reference holds there)
      for (const p of clicks) {
        const a = toCourt(fit.homography!, p)!;
        const b = toCourt(expected, p)!;
        expect(Math.hypot(a[0] - b[0], a[1] - b[1])).toBeLessThan(0.3);
        // and in pixels: the court near each click lies where the reference puts it
        expect(Math.hypot(...(project(fit.homography!, b).map((v, i) => v - p[i]!) as [number, number]))).toBeLessThan(frame.expected_median_px! * 4 + 3);
      }
      expect(fit.medianPx!).toBeLessThanOrEqual(frame.expected_median_px! + 0.3);
    });
  }

  it("drops one click on a neighbouring line", () => {
    const frame = FRAMES.find((f) => f.frame === "c012_00170")!;
    const fit = fitClicks({ points: frame.points, lines: frame.lines }, SIZE);
    expect(fit.dropped.length).toBeGreaterThanOrEqual(1);
    expect(fit.status).toBe("ok");
    expect(fit.medianPx!).toBeLessThanOrEqual(MAX_MEDIAN_PX);
  });

  it("refuses too few clicks to check, but draws a court from eight equations", () => {
    const few: Clicks = { points: { corner_tl: [500, 300] }, lines: { side_near: on(CAMERA, "side_near", [0.1, 0.3]), goal_left: on(CAMERA, "goal_left", [0.3, 0.7]) } };
    expect(equations(few)).toBe(6);
    expect(fitClicks(few, SIZE).status).toBe("too-few");
    const eight: Clicks = {
      points: {},
      lines: {
        side_near: on(CAMERA, "side_near", [0.05, 0.3]),
        side_far: on(CAMERA, "side_far", [0.05, 0.3]),
        goal_left: on(CAMERA, "goal_left", [0.3, 0.7]),
        six_left: on(CAMERA, "six_left", [0.3, 0.7]),
      },
    };
    const fit = fitClicks(eight, SIZE);
    expect(fit.status).toBe("need-more");
    expect(fit.homography).not.toBeNull();
  });

  it("refuses clicks that disagree and names the line", () => {
    const clicks: Clicks = {
      points: {},
      lines: {
        side_near: on(CAMERA, "side_near", [0.05, 0.15, 0.3]),
        side_far: on(CAMERA, "side_far", [0.05, 0.2, 0.35]),
        goal_left: on(CAMERA, "goal_left", [0.3, 0.7]),
        // the 9 m clicks put on the 6 m line and the other way round: no court explains both
        nine_left: on(CAMERA, "six_left", [0.2, 0.4, 0.6, 0.8]),
        six_left: on(CAMERA, "nine_left", [0.2, 0.4, 0.6, 0.8]),
      },
    };
    const fit = fitClicks(clicks, SIZE);
    expect(fit.status).toBe("disagree");
    expect(fit.worst).not.toBeNull();
  });

  it("refits fast from a known court while a click is dragged", () => {
    const clicks: Clicks = {
      points: {},
      lines: {
        side_near: on(CAMERA, "side_near", [0.05, 0.15, 0.3]),
        side_far: on(CAMERA, "side_far", [0.05, 0.2, 0.35]),
        goal_left: on(CAMERA, "goal_left", [0.3, 0.7]),
        six_left: on(CAMERA, "six_left", [0.2, 0.5, 0.8]),
      },
    };
    const moved = { ...clicks, lines: { ...clicks.lines, side_near: clicks.lines.side_near!.map(([x, y]) => [x + 1, y + 1] as Pt) } };
    const fit = fitClicks(moved, SIZE, LOCAL_COURT_MODEL, CAMERA);
    expect(fit.status).toBe("ok");
    expect(fit.medianPx!).toBeLessThan(2);
  });

  it("expresses the fitted court as points the server's point fit takes back exactly", () => {
    const frame = FRAMES[0]!;
    const fit = fitClicks({ points: frame.points, lines: frame.lines }, frame.image_size);
    const pts = courtAsPoints(fit.homography!, { points: frame.points, lines: frame.lines })!;
    expect(pts.length).toBeGreaterThanOrEqual(4);
    expect(pts.every((p) => p.court[0] >= 0 && p.court[0] <= 40 && p.court[1] >= 0 && p.court[1] <= 20)).toBe(true);
    const back = fitHomography(pts.map((p) => p.court), pts.map((p) => p.image))!;
    const near = [...Object.values(frame.points), ...Object.values(frame.lines).flat()].map((p) => toCourt(fit.homography!, p)!);
    for (const c of near) {
      const a = toImage(back, c)!;
      const b = project(fit.homography!, c);
      expect(Math.hypot(a[0] - b[0], a[1] - b[1])).toBeLessThan(0.5);
    }
  });

  it("knows the nine lines and draws them only in front of the camera", () => {
    expect(LINE_NAMES.every((n) => n in LOCAL_COURT_MODEL.lines)).toBe(true);
    const lines = linePolylines(CAMERA, LOCAL_COURT_MODEL.lines.six_left!.court);
    expect(lines.flat().length).toBeGreaterThan(10);
    const behind = [
      [1, 0, 0],
      [0, 1, 0],
      [-0.1, 0, 1],
    ];
    expect(linePolylines(behind, LOCAL_COURT_MODEL.lines.side_near!.court).flat().every(([x]) => Number.isFinite(x))).toBe(true);
  });
});

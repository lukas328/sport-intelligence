import { describe, expect, it } from "vitest";
import { COURT_LANDMARKS, courtPolylines, fitHomography, reprojectionPx, toImage, wellSpread, type Pt } from "./court-calibration";

// a perspective view of the court (balcony camera), court metres -> panorama pixels
const H = [
  [60, 25, 400],
  [0, -18, 900],
  [0, 0.012, 1],
];

describe("court calibration", () => {
  it("recovers the homography from four or more clicked landmarks", () => {
    const court = COURT_LANDMARKS.slice(0, 6).map((l) => l.court);
    const image = court.map((c) => toImage(H, c)!);
    const h = fitHomography(court, image)!;
    expect(h).not.toBeNull();
    for (const p of [[13, 7], [40, 20], [6, 11.5]] as Pt[]) {
      const a = toImage(h, p)!;
      const b = toImage(H, p)!;
      expect(Math.hypot(a[0] - b[0], a[1] - b[1])).toBeLessThan(1e-6);
    }
    expect(reprojectionPx(h, court, image)).toBeLessThan(1e-6);
  });

  it("needs at least four points that are not collinear", () => {
    const court: Pt[] = [[0, 0], [10, 0], [20, 0], [30, 0]];
    expect(fitHomography(court.slice(0, 3), court.slice(0, 3))).toBeNull();
    expect(fitHomography(court, court.map((c) => toImage(H, c)!))).toBeNull();
  });

  it("spreads clicking errors instead of following one bad click", () => {
    const court = COURT_LANDMARKS.map((l) => l.court);
    const image = court.map((c, i) => {
      const p = toImage(H, c)!;
      return [p[0] + (i % 2 ? 1.5 : -1.5), p[1]] as Pt;
    });
    expect(reprojectionPx(fitHomography(court, image)!, court, image)).toBeLessThan(2);
  });

  it("draws the court lines and skips parts behind the camera", () => {
    const lines = courtPolylines(H);
    expect(lines.length).toBeGreaterThan(5);
    expect(lines.every((l) => l.every(([x, y]) => Number.isFinite(x) && Number.isFinite(y)))).toBe(true);
    const behind = [
      [1, 0, 0],
      [0, 1, 0],
      [-0.1, 0, 1],
    ]; // w < 0 for court x > 10: only the left quarter of the court is in front
    const front = courtPolylines(behind);
    expect(front.flat().every(([x, y]) => Number.isFinite(x) && Number.isFinite(y))).toBe(true);
    expect(front.flat().length).toBeLessThan(lines.flat().length / 2);
  });

  it("flags point sets that do not span the court", () => {
    const posts: Pt[] = [[0, 8.5], [0, 11.5], [40, 8.5], [40, 11.5]];
    expect(wellSpread(posts)).toBe(false);
    expect(wellSpread([[0, 0], [0, 20], [40, 0], [40, 20]])).toBe(true);
    expect(wellSpread([...posts, [20, 0], [20, 20]])).toBe(true);
  });

  it("has unique landmark ids inside the court", () => {
    expect(new Set(COURT_LANDMARKS.map((l) => l.id)).size).toBe(COURT_LANDMARKS.length);
    expect(COURT_LANDMARKS.every(({ court: [x, y] }) => x >= 0 && x <= 40 && y >= 0 && y <= 20)).toBe(true);
  });
});

import { describe, expect, it } from "vitest";
import { CORNERS, cornersOf } from "./field-corners";
import { fitHomography, type Pt } from "./court-calibration";

// UX test B13/B14: Prüfen draws the stored court back onto the hall image (court to image) and
// lets the four corners be moved; four moved corners make a court of their own again.
describe("court corners in Prüfen", () => {
  const image: Pt[] = [
    [120, 610],
    [1790, 640],
    [1500, 260],
    [380, 240],
  ];
  it("projects the stored court back onto its corners", () => {
    const h = fitHomography([...CORNERS], image)!;
    cornersOf(h, [1920, 1080]).forEach((p, i) => {
      expect(p[0]).toBeCloseTo(image[i]![0], 3);
      expect(p[1]).toBeCloseTo(image[i]![1], 3);
    });
  });
  it("starts from a frame inside the image without a court in that space", () => {
    const c = cornersOf(null, [1000, 500]);
    expect(c).toHaveLength(4);
    expect(c.every(([x, y]) => x > 0 && x < 1000 && y > 0 && y < 500)).toBe(true);
  });
  it("turns four moved corners into a court again", () => {
    const moved: Pt[] = image.map(([x, y]) => [x + 15, y - 10]);
    const h = fitHomography([...CORNERS], moved);
    expect(h).not.toBeNull();
    expect(cornersOf(h, [1920, 1080])[2]![0]).toBeCloseTo(1515, 3);
  });
});

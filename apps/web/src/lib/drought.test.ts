import { describe, expect, it } from "vitest";
import { ownDrought } from "./drought";

const pts = (own: number[]) => [{ clock_s: 0, own: 0 }, ...own.map((t, i) => ({ clock_s: t, own: i + 1 }))];

describe("ownDrought", () => {
  it("keeps the server's value for a whole game", () => {
    expect(ownDrought(pts([600]), null, 600)).toBe(600);
  });
  it("measures a clip from minute 8 to 13 only where it is seen", () => {
    // clip 1 of the fourth real-video test: own goals at 8:15, 9:01, 10:41, 11:49
    expect(ownDrought(pts([495, 541, 641, 709]), [8, 13], 495)).toBe(100);
  });
  it("counts to the end of the clip when no own goal falls late", () => {
    expect(ownDrought(pts([490]), [8, 13], 490)).toBe(290);
  });
  it("a clip without own goals is one phase", () => {
    expect(ownDrought([{ clock_s: 0, own: 0 }], [8, 13], 0)).toBe(300);
  });
});

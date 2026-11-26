import { describe, expect, it } from "vitest";
import { meanHex, videoPoint } from "./pick-colour";

describe("videoPoint: the video pixel under a tap (object-fit: contain)", () => {
  it("maps a tap on the picture to its pixel", () => {
    // 1280 x 720 shown in 640 x 360: half the size
    expect(videoPoint(320, 180, 640, 360, 1280, 720)).toEqual({ x: 640, y: 360 });
  });

  it("knows the black bars of a portrait video in a wide box and answers nothing there", () => {
    // 720 x 1280 in 640 x 360: shown 202.5 px wide in the middle
    expect(videoPoint(10, 180, 640, 360, 720, 1280)).toBeNull();
    expect(videoPoint(320, 180, 640, 360, 720, 1280)).toEqual({ x: 360, y: 640 });
    expect(videoPoint(1, 1, 0, 0, 1280, 720)).toBeNull();
  });
});

describe("meanHex: the colour around a tap", () => {
  it("averages the pixels, as #rrggbb", () => {
    expect(meanHex([200, 30, 30, 255, 210, 40, 40, 255])).toBe("#cd2323");
    expect(meanHex([0, 0, 0, 255])).toBe("#000000");
    expect(meanHex([])).toBeNull();
  });
});

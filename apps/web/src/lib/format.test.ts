import { describe, expect, it } from "vitest";
import { formatBytes, formatClock, parseThumbVtt } from "./format";

describe("format", () => {
  it("formats clocks", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(61_500)).toBe("1:01");
    expect(formatClock(3_725_000)).toBe("1:02:05");
  });
  it("formats bytes", () => {
    expect(formatBytes(500)).toBe("500 B");
    expect(formatBytes(2.5 * 1024 ** 3)).toBe("2.5 GB");
  });
  it("parses thumbnail vtt", () => {
    const vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:10.000\nthumbs.jpg#xywh=0,0,160,90\n\n00:00:10.000 --> 00:00:20.000\nthumbs.jpg#xywh=160,0,160,90\n";
    const cues = parseThumbVtt(vtt, "/media/");
    expect(cues).toHaveLength(2);
    expect(cues[1]).toEqual({ start: 10, end: 20, url: "/media/thumbs.jpg", x: 160, y: 0, w: 160, h: 90 });
  });
});

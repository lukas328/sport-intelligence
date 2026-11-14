import { describe, expect, it } from "vitest";
import { MIB, level, mayUpload, minutesLeft, missing, parse, planParts, preflight, progress, requiredBytes } from "./index";

const ORG = "11111111-1111-1111-1111-111111111111";
const MATCH = "22222222-2222-2222-2222-222222222222";

describe("upload plan", () => {
  it("splits into parts and resumes with the missing ones", () => {
    const parts = planParts(40 * MIB, 16 * MIB);
    expect(parts.map((p) => [p.number, p.end - p.start])).toEqual([[1, 16 * MIB], [2, 16 * MIB], [3, 8 * MIB]]);
    expect(missing(parts, [1, 3]).map((p) => p.number)).toEqual([2]);
    expect(progress(parts, [1, 3])).toBeCloseTo(0.6);
    expect(planParts(0)).toEqual([]);
    expect(progress([], [])).toBe(1);
  });

  it("waits for Wi-Fi with large uploads", () => {
    expect(mayUpload("wifi", 5_000 * MIB, false)).toBe(true);
    expect(mayUpload("cellular", 5_000 * MIB, false)).toBe(false);
    expect(mayUpload("cellular", 5_000 * MIB, true)).toBe(true);
    expect(mayUpload("cellular", 50 * MIB, false)).toBe(true);
    expect(mayUpload("none", 1, true)).toBe(false);
  });
});

describe("recording checks", () => {
  it("needs room for 70 minutes at 1080p50", () => {
    expect(requiredBytes()).toBe(10_500_000_000);
    expect(preflight({ freeBytes: 20e9, batteryLevel: 0.9, charging: false })).toEqual([]);
    expect(preflight({ freeBytes: 8e9, batteryLevel: 0.3, charging: false })).toEqual(["storage", "battery"]);
    expect(preflight({ freeBytes: 20e9, batteryLevel: 0.3, charging: true })).toEqual([]);
    expect(minutesLeft(15e9)).toBe(100);
  });

  it("tells how the phone is tilted", () => {
    expect(level(-1, 0, 0)).toBe("level");
    expect(level(-1, 0.1, 0)).toBe("tilted_right");
    expect(level(-1, -0.1, 0)).toBe("tilted_left");
    expect(level(-0.8, 0, 0.5)).toBe("tilted_back");
    expect(level(-0.8, 0, -0.5)).toBe("tilted_forward");
  });
});

describe("deep links", () => {
  it("opens clips, matches and lists", () => {
    expect(parse(`handball://clip/${MATCH}?t=61000`)).toEqual({ screen: "clip", matchId: MATCH, t: 61000 });
    expect(parse(`https://app.handball-intelligence.com/app/${ORG}/matches/${MATCH}?t=5000`)).toEqual({ screen: "match", orgId: ORG, matchId: MATCH, t: 5000 });
    expect(parse(`/app/${ORG}/assignments`)).toEqual({ screen: "assignments", orgId: ORG });
    expect(parse(`/app/${ORG}/feed`)).toEqual({ screen: "feed", orgId: ORG });
    expect(parse(`/app/${ORG}/presentations/${MATCH}/present`)).toEqual({ screen: "presentation", orgId: ORG, presentationId: MATCH, key: null });
    expect(parse(`/app/${ORG}/presentations/${MATCH}/remote?k=abc`)).toMatchObject({ key: "abc" });
    expect(parse(`handball://clip/${MATCH}?t=-4`)).toEqual({ screen: "clip", matchId: MATCH, t: 0 });
    expect(parse("javascript:alert(1)")).toEqual({ screen: "home" });
    expect(parse(null)).toEqual({ screen: "home" });
    expect(parse("/app/not-a-uuid/feed")).toEqual({ screen: "home" });
  });
});

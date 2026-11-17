import { describe, expect, it } from "vitest";
import { filesSummary, personGroups } from "./check-budget";
import { checkCount, openMoments, type MatchGraphics } from "./graphics";
import { nameDate, nameWords, otherGame } from "./file-match";

const track = (track_no: number, first_ms: number, last_ms: number, number: number | null = null) => ({ track_no, first_ms, last_ms, number });

describe("the people in the picture, bundled (second round A6)", () => {
  it("asks once per person, the longest seen first, at most three", () => {
    const tracks = [
      track(1, 0, 8000, 7), // number 7 in three scenes: one question
      track(2, 20_000, 40_000, 7),
      track(3, 60_000, 62_000, 7), // too short to recognise anyone: left out
      track(4, 5000, 15_000, null),
      track(5, 30_000, 36_000, 11),
      track(6, 50_000, 51_000, null), // too short: never asked
      track(7, 70_000, 90_000, null),
    ];
    const groups = personGroups(tracks, 5000, 3);
    expect(groups).toHaveLength(3);
    // number 7 (28 s), track 7 (20 s), track 4 (10 s); number 11 (6 s) waits
    expect(groups.map((g) => g.map((t) => t.track_no))).toEqual([[4], [2, 1], [7]]);
    // the scene shown is the longest of the person
    expect(groups[1]![0]!.track_no).toBe(2);
    expect(personGroups(tracks, 5000, 6).flat().some((t) => t.track_no === 6)).toBe(false);
  });
});

describe("the files of a match together (second round A8)", () => {
  it("sums up several files, says nothing for one", () => {
    expect(filesSummary([{ state: "ready" }])).toBeNull();
    expect(filesSummary([{ state: "ready" }, { state: "failed" }])).toEqual({ total: 2, ready: 1, failed: 1, running: 0 });
    expect(filesSummary([{ state: "ready" }, { state: "running" }, { state: "ready" }])).toEqual({ total: 3, ready: 2, failed: 0, running: 1 });
  });
});

describe("the count of Prüfen is the budget only (second round A6)", () => {
  const check = (kind: string, id: string) => ({ id, kind, frame_ref: 0, box: null, seconds_in_view: null, suggested_side: null, candidates: [] });
  const g = (checks: ReturnType<typeof check>[], more: ReturnType<typeof check>[]) => ({ checks, more_checks: more }) as unknown as MatchGraphics;

  it("never counts what waits behind «Mehr prüfen»", () => {
    const more = Array.from({ length: 150 }, (_, i) => check("goal", `m${i}`));
    expect(checkCount(g([], more))).toBe(0);
    expect(openMoments(g([], more))).toBe(0);
    expect(checkCount(g([check("field", "f"), check("goal", "a"), check("goal", "b")], more))).toBe(3);
    expect(openMoments(g([check("field", "f"), check("goal", "a")], more))).toBe(1);
  });
});

describe("a second file of another game (second round A5)", () => {
  it("reads team words from file names", () => {
    expect(nameWords("DE_3Liga_HSGKonstanz_vs_TSVHaunstetten.mp4")).toEqual(["hsg", "konstanz", "tsv", "haunstetten"]);
    expect(nameWords("GX010123.MP4")).toEqual([]);
    expect(nameDate("Horgen_2026-11-15_HZ1.mp4")).toBe("20261115");
    expect(nameDate("Spiel 15.11.2026.mov")).toBe("20261115");
    expect(nameDate("GX010123.MP4")).toBeNull();
  });

  it("warns when the names name other teams or another day, never for camera names or halves", () => {
    expect(otherGame("DE_3Liga_HSGKonstanz_TSVHaunstetten.mp4", ["CH_NLB_SGHorgen_Endingen.mp4"])).toBe("CH_NLB_SGHorgen_Endingen.mp4");
    expect(otherGame("Horgen Endingen 2. Halbzeit.mp4", ["Horgen Endingen 1. Halbzeit.mp4"])).toBeNull();
    expect(otherGame("GX020123.MP4", ["GX010123.MP4"])).toBeNull();
    expect(otherGame("Horgen_2026-11-15.mp4", ["Horgen_2026-11-08.mp4"])).toBe("Horgen_2026-11-08.mp4");
    expect(otherGame("spiel.mp4", [])).toBeNull();
    expect(otherGame("Konstanz Haunstetten.mp4", ["IMG_4411.MOV"])).toBeNull();
  });
});

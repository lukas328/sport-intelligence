import { describe, expect, it } from "vitest";
import { isShort, latestJobs, mainFiles, partAt, partName, swappable, partStarts, partState, partsOf, recordingOrder, timelineVideo, type PartVideo } from "./video-parts";

const v = (id: string, extra: Partial<PartVideo> = {}): PartVideo => ({ id, role: "main", status: "ready", filename: `${id}.mp4`, duration_s: 1800, part: null, part_start_ms: null, ...extra });

describe("a match in several files (Q-VIDEO-PARTS)", () => {
  const first = v("a", { part: 1, part_start_ms: 0 });
  const second = v("b", { part: 2, part_start_ms: 1_800_000, duration_s: 1750 });
  const goalCam = v("g", { role: "goal_cam_left" });

  it("plays the first part as long as all parts together", () => {
    const tl = timelineVideo([second, goalCam, first])!;
    expect(tl.id).toBe("a");
    expect(tl.duration_s).toBe(3550);
    // one file: as it is
    expect(timelineVideo([v("x")])).toEqual(v("x"));
    // the second part's length not known yet: the first's
    expect(timelineVideo([first, { ...second, duration_s: null }])!.duration_s).toBe(1800);
  });

  it("orders the parts and lists files on their way after them", () => {
    const copy = v("c", { duplicate_of: "a", status: "failed" });
    expect(partsOf([second, first, goalCam]).map((x) => x.id)).toEqual(["a", "b"]);
    expect(mainFiles([copy, second, first, goalCam]).map((x) => x.id)).toEqual(["a", "b", "c"]);
  });

  it("knows where each half starts and which half a time is in", () => {
    expect(partStarts([first, second])).toEqual([{ part: 2, start_ms: 1_800_000, video_id: "b" }]);
    expect(partAt([first, second], 1_900_000)).toEqual({ video: second, local_ms: 100_000 });
    expect(partAt([first, second], -500)!.video.id).toBe("a");
    expect(partAt([v("x")], 10)).toBeNull();
  });

  it("calls two parts halves and more parts parts", () => {
    // the API says which parts are halves (a side change between them)
    const a = v("a", { part: 1, part_start_ms: 0, half: 1 });
    const b = v("b", { part: 2, part_start_ms: 1_800_000, half: 2 });
    expect(partName(2, [a, b])).toEqual({ key: "half", n: 2 });
    // a recording the phone split: no side change, «Teil 1 / Teil 2» (Echtlauf 5 P9)
    expect(partName(2, [{ ...a, half: null }, { ...b, half: null }])).toEqual({ key: "part", n: 2 });
    // a short third file does not make the halves «Teil n», nor hide the swap (P6)
    const c = v("c", { part: 3, part_start_ms: 3_550_000, duration_s: 5 });
    expect(partName(2, [a, b, c])).toEqual({ key: "half", n: 2 });
    expect(partName(3, [a, b, c])).toEqual({ key: "part", n: 3 });
    expect(swappable([a, b, c])?.map((x) => x.id)).toEqual(["a", "b"]);
    expect(swappable([a, b, { ...c, duration_s: 1200 }])).toBeNull();
  });

  it("says what each file is doing from its newest jobs", () => {
    const job = (status: string, progress = 0.5, kind = "analysis", video = "b") => ({ id: `${kind}-${status}`, kind, status, progress, video_asset_id: video });
    expect(partState(second, [job("running", 0.4)])).toEqual({ kind: "analysing", progress: 0.4 });
    expect(partState(second, [job("failed")])).toEqual({ kind: "analysisFailed" });
    expect(partState(second, [])).toEqual({ kind: "notAnalysed" });
    expect(partState({ ...second, status: "processing" }, [])).toEqual({ kind: "processing" });
    expect(partState(v("c", { duplicate_of: "a", status: "failed" }), [])).toEqual({ kind: "duplicate" });
    // a failed run and a new one: the new one counts
    const jobs = latestJobs([job("succeeded", 1), { ...job("failed"), id: "old" }]);
    expect(partState(second, jobs)).toEqual({ kind: "ready" });
  });

  it("spots a part started by mistake", () => {
    expect(isShort(v("s", { duration_s: 5 }), [first])).toBe(true);
    expect(isShort(first, [first, v("s", { duration_s: 5 })])).toBe(false);
    expect(isShort(v("u", { duration_s: null }), [first])).toBe(false);
    // two short clips side by side: neither is a mistake
    expect(isShort(v("p", { duration_s: 15 }), [v("q", { duration_s: 15 })])).toBe(false);
  });

  it("uploads files chosen together in the order they were recorded", () => {
    const f = (name: string, lastModified: number) => ({ name, lastModified });
    expect(recordingOrder([f("IMG_0413.MOV", 2000), f("IMG_0412.MOV", 1000)]).map((x) => x.name)).toEqual(["IMG_0412.MOV", "IMG_0413.MOV"]);
    expect(recordingOrder([f("teil10.mp4", 5), f("teil9.mp4", 5)]).map((x) => x.name)).toEqual(["teil9.mp4", "teil10.mp4"]);
  });
});

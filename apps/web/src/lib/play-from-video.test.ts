import { afterEach, describe, expect, it, vi } from "vitest";
import { playFromVideo } from "./play-from-video";

function chunk(rows: number[][]): ArrayBuffer {
  return new Float32Array(rows.flat()).buffer;
}

afterEach(() => vi.unstubAllGlobals());

describe("playFromVideo", () => {
  it("takes the closest row per track and maps teams", async () => {
    const fetchMock = vi.fn(async () => new Response(chunk([
      [30_960, 1, 10, 5],
      [31_000, 1, 11, 5], // closest for track 1
      [31_040, 2, 30, 10],
      [31_000, 3, 39, 10], // goalkeeper
      [31_000, 4, 20, 10], // referee: left out
      [32_000, 5, 25, 3], // too far in time
    ])));
    vi.stubGlobal("fetch", fetchMock);
    const doc = await playFromVideo("/v1/x/tracks", 30_000, 31_000, [
      { track_no: 1, team: "home", number: 7 },
      { track_no: 2, team: "away" },
      { track_no: 3, team: "home_gk" },
      { track_no: 4, team: "referee" },
      { track_no: 5, team: "away" },
    ]);
    expect(fetchMock).toHaveBeenCalledWith("/v1/x/tracks/1", { credentials: "same-origin" });
    expect(doc?.court).toBe("full");
    expect(doc?.frames[0]!.tokens.map((t) => [t.side, t.label, t.x])).toEqual([
      ["own", "7", 11],
      ["own", "TW", 39],
      ["opp", "3", 30],
    ]);
  });

  it("returns null without data", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 404 })));
    expect(await playFromVideo("/x", 30_000, 0, [])).toBeNull();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(chunk([[0, 1, 1, 1]]))));
    expect(await playFromVideo("/x", 30_000, 0, [{ track_no: 1, team: "referee" }])).toBeNull();
  });
});

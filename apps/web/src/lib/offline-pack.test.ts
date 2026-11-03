import { describe, expect, it } from "vitest";
import { lowestVariant, parseMediaPlaylist } from "./offline-pack";

describe("offline presentation pack", () => {
  it("picks the lowest variant", () => {
    const master = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=5000000\n1080p/index.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=2500000\n720p/index.m3u8\n";
    expect(lowestVariant(master)).toBe("720p/index.m3u8");
  });
  it("maps segments to times", () => {
    const pl = '#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\n#EXTINF:4.0,\nseg0.m4s\n#EXTINF:4.0,\nseg1.m4s\n#EXTINF:2.5,\nseg2.m4s\n#EXT-X-ENDLIST\n';
    const { init, segments } = parseMediaPlaylist(pl);
    expect(init).toBe("init.mp4");
    expect(segments.map((s) => [s.uri, s.start, s.end])).toEqual([
      ["seg0.m4s", 0, 4],
      ["seg1.m4s", 4, 8],
      ["seg2.m4s", 8, 10.5],
    ]);
  });
});

import { describe, expect, it } from "vitest";
import { positionAt, presence, trailAt, type Pt } from "@/components/anlauf/geometry";

// real-video test F5: scene 1 drew 13 own dots for 7 players, because each piece of a track
// was a dot for the whole scene, stretched over it without its times
const piece = (from: number, to: number, x: number): { xy: Pt[]; ts: number[] } => {
  const ts = [from, (from + to) / 2, to];
  return { xy: ts.map((t) => [x + t * 10, 5] as Pt), ts };
};

describe("tactics camera over time", () => {
  it("shows at no moment more dots than tracks that exist then", () => {
    // seven players, each seen in two pieces with a gap (the tracker lost and found them)
    const tracks = Array.from({ length: 7 }, (_, i) => [piece(0, 0.45, i), piece(0.55, 1, i)]).flat();
    for (let t = 0; t <= 1; t += 0.01) {
      const alive = tracks.filter((x) => t >= x.ts[0]! && t <= x.ts[x.ts.length - 1]!).length;
      const shown = tracks.filter((x) => presence(x.ts, t) > 0).length;
      // a track fades out briefly after its last point: at most the piece before the gap
      expect(shown).toBeLessThanOrEqual(Math.max(alive, 7));
      expect(shown).toBeLessThanOrEqual(14);
    }
    expect(tracks.filter((x) => presence(x.ts, 0.5) > 0)).toHaveLength(0);
    expect(tracks.filter((x) => presence(x.ts, 0.2) > 0)).toHaveLength(7);
  });

  it("places a track by its own times and draws its way only where it has data", () => {
    const p = piece(0.2, 0.6, 0);
    expect(positionAt(p.xy, p.ts, 0.4)).toEqual([4, 5]);
    expect(positionAt(p.xy, p.ts, 0.1)).toEqual(p.xy[0]);
    expect(trailAt(p.xy, p.ts, 0.25, 0.33).length).toBeGreaterThan(0);
    expect(trailAt(p.xy, p.ts, 0.1, 0.05)).toEqual([]);
    // a drawn scene without times keeps its track for the whole scene
    expect(presence(null, 0.9)).toBe(1);
  });
});

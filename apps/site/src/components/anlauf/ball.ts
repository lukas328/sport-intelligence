/**
 * Where the ball is in a scene of the tactics camera. Plain TypeScript (no JSX), so that tests can
 * use it. Site only: the app draws the ball at its holder; the website's invented demo also knows
 * its passes.
 */
import { type Pt, sampleAt } from "./geometry";
import type { BallStretch, CameraScene, SceneTrack } from "./tactics-camera";

export function holderAt(scene: CameraScene, t: number): BallStretch | null {
  const sec = t * scene.duration;
  return scene.ball.find((b) => sec >= b.from && sec <= b.to) ?? null;
}

/** Longest gap between two holders that is drawn as a pass (site only: the demo is invented). */
export const PASS_MAX_S = 1;

function trackOf(scene: CameraScene, team: "own" | "opp", number: number): SceneTrack | undefined {
  return scene.tracks.find((x) => x.team === team && x.number === number);
}

/**
 * Where the ball is at t, in court metres: at the player who holds it, or on the short way of a
 * pass between two holders. Null where it was not found. (The app draws it at the holder only;
 * the website's invented demo knows its passes.)
 */
export function ballAt(scene: CameraScene, t: number): Pt | null {
  const hold = holderAt(scene, t);
  if (hold) {
    const tr = trackOf(scene, hold.team, hold.number);
    return tr ? sampleAt(tr.xy, t) : null;
  }
  const sec = t * scene.duration;
  const i = scene.ball.findIndex((b) => b.from > sec);
  if (i <= 0) return null;
  const a = scene.ball[i - 1]!;
  const b = scene.ball[i]!;
  if (b.from - a.to > PASS_MAX_S) return null;
  const ta = trackOf(scene, a.team, a.number);
  const tb = trackOf(scene, b.team, b.number);
  if (!ta || !tb) return null;
  const pa = sampleAt(ta.xy, a.to / scene.duration);
  const pb = sampleAt(tb.xy, b.from / scene.duration);
  const f = (sec - a.to) / (b.from - a.to);
  return [pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f];
}

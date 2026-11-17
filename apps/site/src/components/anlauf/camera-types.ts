/** Data of the tactics camera (kept apart so ball.ts and the camera can share them without a cycle). */
import type { Pt } from "./geometry";

/** One tracked person of a scene, in court metres (40 x 20). */
export interface SceneTrack {
  team: "own" | "opp" | "ref";
  /** shirt number, only where it was read */
  number?: number | null;
  /** the goalkeeper (the only one who may stand in the goal area) */
  keeper?: boolean;
  xy: readonly Pt[];
}

/** A stretch where the ball was found in the picture and the analysis knows who holds it. */
export interface BallStretch {
  /** seconds from the scene start */
  from: number;
  to: number;
  team: "own" | "opp";
  number: number;
}

export interface CameraScene {
  /** match clock at the scene start, seconds */
  clock: number;
  /** length in seconds */
  duration: number;
  tracks: readonly SceneTrack[];
  /** empty: the ball was not found in this scene; nothing is drawn for it */
  ball: readonly BallStretch[];
  scorer?: { team: "own" | "opp"; number: number } | null;
  shot?: Pt | null;
  aim?: Pt | null;
  /** the scorer's way: solid when confirmed, dashed when estimated */
  confirmed: boolean;
  /** label at the shot spot, e.g. "Tor Thalwil 39:55" */
  label?: string | null;
}

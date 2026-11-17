/** Types of the drill library (kept apart from drills.ts so the drill lists can import them without a cycle). */
import type { Arrow, Token } from "./format";

export type Focus =
  | "finishing"
  | "wings"
  | "back_court"
  | "pivot"
  | "seven_m"
  | "goalkeeping"
  | "passing"
  | "transition_defence"
  | "fast_break"
  | "defence"
  | "powerplay";

export const FOCI: Focus[] = ["finishing", "wings", "back_court", "pivot", "seven_m", "goalkeeping", "passing", "transition_defence", "fast_break", "defence", "powerplay"];

export type Lang = "de-CH" | "en" | "fr";
export type Text = Record<Lang, string>;
export type Level = "basic" | "advanced";

/** A drill drawn on the board: blue are the players who practise, orange their opponents. */
export interface DrillSketch {
  court: "half" | "full";
  tokens: Token[];
  ball: { x: number; y: number } | null;
  arrows: Arrow[];
  cones: [number, number][];
}

export interface Drill {
  id: string;
  focus: Focus[];
  minutes: number;
  players: string; // e.g. "6-12"
  level: Level;
  name: Text;
  setup: Text;
  procedure: Text;
  coaching: Text;
  variants: Text;
  sketch: DrillSketch;
}

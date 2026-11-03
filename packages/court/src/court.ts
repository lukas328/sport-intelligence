import geometry from "../generated/court_geometry.json";

export type Point = readonly [number, number];

export interface Court {
  length: number;
  width: number;
  goal: { width: number; height: number };
  goalAreaRadius: number;
  freeThrowRadius: number;
  dashedLines: readonly string[];
  lines: Readonly<Record<string, readonly Point[]>>;
  keypoints: Readonly<Record<string, Point>>;
}

export const COURT: Court = {
  length: geometry.length,
  width: geometry.width,
  goal: geometry.goal,
  goalAreaRadius: geometry.goal_area_radius,
  freeThrowRadius: geometry.free_throw_radius,
  dashedLines: geometry.dashed_lines,
  lines: geometry.lines as unknown as Record<string, readonly Point[]>,
  keypoints: geometry.keypoints as unknown as Record<string, Point>,
};

/** Normalise so that the attacked goal is always at x = length (rotation by 180° otherwise). */
export function normalizeToAttack(p: Point, attackingRight: boolean, court: Court = COURT): Point {
  return attackingRight ? p : [court.length - p[0], court.width - p[1]];
}

/** Distance (m) from a normalised position to the goal at x = length. */
export function distanceToAttackedGoal(p: Point, court: Court = COURT): number {
  const half = court.goal.width / 2;
  const cy = court.width / 2;
  const gy = Math.min(Math.max(p[1], cy - half), cy + half);
  return Math.hypot(court.length - p[0], p[1] - gy);
}


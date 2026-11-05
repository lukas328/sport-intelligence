import spec from "../spec/zones.json";
import { COURT, distanceToAttackedGoal } from "./court";

export type ShotZone = (typeof spec.zones)[number];
export const SHOT_ZONES = spec.zones as readonly string[];
export const GOAL_ZONES = ["TL", "TC", "TR", "ML", "MC", "MR", "BL", "BC", "BR"] as const;
export type GoalZone = (typeof GOAL_ZONES)[number];
export const ZONE_LABELS: Record<string, string> = spec.labels["de-CH"];

/** Zone of a shot from its normalised position (attacked goal at x = 40). Mirrors zones.py. */
export function shotZone(
  x: number,
  y: number,
  opts: { penalty?: boolean; fastBreak?: boolean; emptyGoal?: boolean } = {},
): string {
  if (opts.penalty) return "penalty";
  if (opts.emptyGoal) return "empty_goal";
  if (opts.fastBreak) return "fast_break";
  const d = distanceToAttackedGoal([x, y]);
  if (d > spec.long_range_m) return "long_range";
  const dy = y - COURT.width / 2;
  const side = dy > 0 ? "left" : "right";
  const w = spec.wing;
  if (x >= w.min_x && Math.abs(dy) >= w.min_abs_dy && d <= w.max_distance_m) return `wing_${side}`;
  const band = d <= spec.circle_max_m ? "circle" : d <= spec.back_min_m ? "half" : "back";
  if (Math.abs(dy) < spec.centre_half_width_m[band]) return `${band}_centre`;
  return `${band}_${side}`;
}

/** Shooter's view <-> goalkeeper's view: left and right swap. */
export function mirrorGoalZone(zone: GoalZone): GoalZone {
  const col = zone[1] === "L" ? "R" : zone[1] === "R" ? "L" : "C";
  return `${zone[0]}${col}` as GoalZone;
}

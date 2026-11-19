/**
 * One account of a side's shots, from the same match statistics every figure of the match comes
 * from (app review BUG-08): the shots on target are its goals, the saves of the other side's
 * keeper, the misses and the posts; blocked shots are counted apart (BRIEF 4.8). A side whose
 * attempts were never recorded beyond its goals has no shot count: «nicht erfasst», not «-» next to
 * a number of the other side.
 */
export interface SideShots {
  goals: number;
  shots: number;
  shots_blocked?: number;
  misses: number;
  posts: number;
  saves: number;
  known?: { shooting: boolean; saving: boolean; turnovers: boolean };
}

export interface ShotBalance {
  /** false: only the goals are known, every other figure is «nicht erfasst» */
  known: boolean;
  shots: number;
  goals: number;
  /** saved by the other side's keeper */
  saved: number;
  misses: number;
  posts: number;
  blocked: number;
  /** shots on target the parts above do not explain (another outcome); 0 when the figures agree */
  other: number;
}

export function shotBalance(side: SideShots, other: SideShots): ShotBalance {
  const known = side.known?.shooting !== false;
  const saved = other.saves;
  const parts = side.goals + saved + side.misses + side.posts;
  return {
    known,
    shots: side.shots,
    goals: side.goals,
    saved,
    misses: side.misses,
    posts: side.posts,
    blocked: side.shots_blocked ?? 0,
    other: Math.max(0, side.shots - parts),
  };
}

/** Shots without a position: always the shots less the shots with one, never a figure of its own. */
export function withoutPosition(shots: number, placed: number): number {
  return Math.max(0, shots - placed);
}

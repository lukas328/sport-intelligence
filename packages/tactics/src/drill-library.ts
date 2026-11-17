/** The drill library in one list, ordered by topic (attack, goalkeeper and passing, game situations). */
import { ATTACK_DRILLS } from "./drills-attack";
import { GAME_DRILLS } from "./drills-game";
import type { Drill } from "./drill-types";
import { KEEPER_PASSING_DRILLS } from "./drills-keeper-passing";

export const DRILL_LIBRARY: Drill[] = [...ATTACK_DRILLS, ...KEEPER_PASSING_DRILLS, ...GAME_DRILLS];

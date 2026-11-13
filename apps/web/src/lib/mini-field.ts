import { VIEWS } from "@/components/anlauf/geometry";

/** The Minifeld of a scene in a list (UX test N07): small, with dots in its own scale. */
export const MINI = { view: "halfB" as const, width: 56, dot: 2.6 };

/** The radius of a player's dot in court metres for a field drawn `width` pixels wide. */
export function dotMetres(width: number, dot: number, view: keyof typeof VIEWS = MINI.view): number {
  return dot / (width / VIEWS[view].box[2]);
}

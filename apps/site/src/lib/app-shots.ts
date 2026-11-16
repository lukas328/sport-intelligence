/**
 * Pictures from the app in public/app, made by scripts/app-screens.mjs. Their pixel sizes come
 * from app-shots.json, which the script writes, so the pages stay right when the pictures are made
 * again.
 */
import sizes from "./app-shots.json";

export type ShotName = keyof typeof sizes;

export function shot(name: ShotName): { src: string; width: number; height: number } {
  return { src: `/app/${name}.webp`, ...sizes[name] };
}

/**
 * Where the bar should be after a scroll step: shown near the top, hidden while scrolling down,
 * shown again on the first step up. `dy` is the change since the last frame; small downward jitter
 * (a finger resting, the address bar sliding) does not hide it.
 */
export function nextHidden(hidden: boolean, y: number, dy: number, barHeight: number): boolean {
  if (y <= barHeight) return false;
  if (dy < 0) return false;
  if (dy > 6) return true;
  return hidden;
}

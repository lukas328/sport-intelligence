/**
 * Best camera per event (addendum 01, 4.5): shots on goal are best seen from the goal camera of
 * that goal. Court x runs 0..40 m; the left goal is at x = 0.
 */
export interface CamInfo {
  id: string;
  role: string;
}
export interface EventInfo {
  type: string;
  t_ms: number | null;
  x: number | null;
  outcome: string | null;
  goal_zone: string | null;
}

export const BEFORE_MS = 4000;
export const AFTER_MS = 2000;

export function bestCamera(e: EventInfo, cams: CamInfo[]): string | null {
  if (e.type !== "shot" || e.x == null) return null;
  if (!e.goal_zone && !["goal", "save", "post"].includes(e.outcome ?? "")) return null;
  const role = e.x < 20 ? "goal_cam_left" : "goal_cam_right";
  return cams.find((c) => c.role === role)?.id ?? null;
}

/** Camera to show at main-video time t: the best camera of an event close to t, else null (main). */
export function cameraAt(t: number, events: EventInfo[], cams: CamInfo[]): string | null {
  for (const e of events) {
    if (e.t_ms == null || t < e.t_ms - BEFORE_MS || t > e.t_ms + AFTER_MS) continue;
    const cam = bestCamera(e, cams);
    if (cam) return cam;
  }
  return null;
}

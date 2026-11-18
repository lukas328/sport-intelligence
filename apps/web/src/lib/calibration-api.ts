/**
 * The API calls of the court calibration dialog, in one place, on the generated client.
 *
 * Line clicks: GET calibration/court-model, POST .../calibration/clicks/check (the server's fit,
 * stores nothing), POST .../calibration/clicks (saved as the coach's court, the analysis runs
 * again), POST .../calibration/undeterminable; in the analysis calibration_state,
 * calibration_suggestion and court_clicks. Each call is still feature-detected (an API without
 * them, e.g. an older deployment): an endpoint that answers a bare 404 is remembered as missing
 * for this page, and the dialog falls back (the local court model and fit, the fitted court as
 * points on the hall image through POST .../calibration, no «Nicht bestimmbar»).
 */
import type { Schemas } from "@handball/api-client";
import { api } from "@/lib/client";
import { courtAsPoints, type ClickRef, type Clicks, type CourtModel, type Pt } from "@/lib/court-fit";
import { courtFromHall, courtFromHallSure } from "@/lib/match-workflow";
import type { Homography } from "@/lib/spotlight";

export type Space = "panorama" | "frame";

/** The body of the check and save calls for line clicks. */
export type ClicksBody = Required<Schemas["CourtClicksIn"]>;
export type DroppedClick = Schemas["DroppedClickOut"];
/** The court through the clicks, with each click's distance (per_click_px). */
export type ServerFit = Schemas["CourtClicksOut"];

export interface ClickProblem {
  /** clicks-too-few, clicks-disagree, clicks-unknown, no-hall-image (409), or another code */
  code: string;
  detail?: string;
  /** clicks-disagree: the click that agrees least, and the median (problem extension members) */
  worst?: DroppedClick & { px?: number };
  median_px?: number;
}

export type Outcome<T> =
  | { kind: "ok"; value: T }
  /** the server refused the clicks (422) or the video is not ready for them (409) */
  | { kind: "refused"; problem: ClickProblem }
  /** the endpoint does not exist: use the fallback */
  | { kind: "missing" }
  | { kind: "error"; status: number };

/** Why the court cannot be read: too far away, cuts in the video, something else. */
export type UndeterminableReason = NonNullable<Schemas["CourtUndeterminableIn"]["reason"]>;

type Endpoint = "court-model" | "clicks/check" | "clicks" | "undeterminable";

/** The endpoints found missing on this page: not asked again. */
const missing = new Set<Endpoint>();

/** Forget what was found missing (tests, or a new page). */
export function resetFeatureDetection(): void {
  missing.clear();
}

export function isMissing(endpoint: Endpoint): boolean {
  return missing.has(endpoint);
}

/** A 404 of the router itself (no such endpoint), not a 404 problem of the API (no such video). */
function routeMissing(status: number, body: unknown): boolean {
  if (status !== 404) return false;
  const type = body && typeof body === "object" && typeof (body as { type?: unknown }).type === "string" ? (body as { type: string }).type : "about:blank";
  return type === "about:blank";
}

function problemOf(raw: unknown): ClickProblem {
  const body = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const type = typeof body.type === "string" ? body.type : "";
  const code = typeof body.code === "string" ? body.code : type.includes(":") ? type.slice(type.lastIndexOf(":") + 1) : type || "error";
  const w = body.worst as Record<string, unknown> | undefined;
  const worst =
    w && (w.kind === "line" || w.kind === "point") && typeof w.name === "string"
      ? { kind: w.kind as DroppedClick["kind"], name: w.name, index: typeof w.index === "number" ? w.index : null, px: typeof w.px === "number" ? w.px : undefined }
      : undefined;
  return { code, detail: typeof body.detail === "string" ? body.detail : undefined, worst, median_px: typeof body.median_px === "number" ? body.median_px : undefined };
}

/** One typed call with the feature detection and the problem reading. */
async function outcome<T>(endpoint: Endpoint | null, call: () => Promise<{ data?: T; error?: unknown; response: Response }>): Promise<Outcome<T>> {
  if (endpoint && missing.has(endpoint)) return { kind: "missing" };
  let r: { data?: T; error?: unknown; response: Response };
  try {
    r = await call();
  } catch {
    return { kind: "error", status: 0 };
  }
  const status = r.response.status;
  if (r.response.ok) return { kind: "ok", value: r.data as T };
  if (endpoint && routeMissing(status, r.error)) {
    missing.add(endpoint);
    return { kind: "missing" };
  }
  if (status === 422 || status === 409) return { kind: "refused", problem: problemOf(r.error) };
  return { kind: "error", status };
}

const isPt = (p: unknown): p is Pt => Array.isArray(p) && p.length === 2 && p.every((v) => typeof v === "number" && Number.isFinite(v));
const path = (orgId: string, videoId: string) => ({ params: { path: { org_id: orgId, video_id: videoId } } });

/** The court model the API fits with; null while it serves none (use LOCAL_COURT_MODEL). */
export async function fetchCourtModel(orgId: string): Promise<CourtModel | null> {
  const r = await outcome("court-model", () => api.GET("/v1/orgs/{org_id}/calibration/court-model", { params: { path: { org_id: orgId } } }));
  if (r.kind !== "ok" || !r.value?.lines) return null;
  const lines: CourtModel["lines"] = {};
  for (const [name, l] of Object.entries(r.value.lines)) {
    if ((l.kind === "line" || l.kind === "arc") && Array.isArray(l.court) && l.court.length >= 2 && l.court.every(isPt)) lines[name] = { kind: l.kind, court: l.court as Pt[] };
  }
  const points: CourtModel["points"] = {};
  for (const [name, p] of Object.entries(r.value.points ?? {})) if (isPt(p)) points[name] = p;
  return Object.keys(lines).length ? { lines, points } : null;
}

/** The server's fit of the clicks (stores nothing, about a second). */
export function checkClicks(orgId: string, videoId: string, body: ClicksBody): Promise<Outcome<ServerFit>> {
  return outcome("clicks/check", () => api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/clicks/check", { ...path(orgId, videoId), body }));
}

/** Save the clicks as the court (a correction; the analysis runs again; later videos of the
 * hall get it offered). */
export function saveClicks(orgId: string, videoId: string, body: ClicksBody): Promise<Outcome<Schemas["CourtClicksJobOut"]>> {
  return outcome("clicks", () => api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/clicks", { ...path(orgId, videoId), body }));
}

/** The dropped clicks of the server as the dialog names clicks. */
export function droppedRefs(d: DroppedClick[] | undefined): ClickRef[] {
  return (d ?? []).map((x): ClickRef => (x.kind === "point" ? { kind: "point", name: x.name } : { kind: "line", name: x.name, index: x.index ?? 0 }));
}

/** Whether «nicht bestimmbar» can be saved: a GET on the POST endpoint answers 405 where it
 * exists (an older API answers 404). */
export async function canMarkUndeterminable(orgId: string, videoId: string): Promise<boolean> {
  if (missing.has("undeterminable")) return false;
  try {
    const res = await fetch(`/v1/orgs/${orgId}/videos/${videoId}/calibration/undeterminable`, { credentials: "same-origin", headers: { accept: "application/json" } });
    if (res.status === 405) return true;
    const json: unknown = await res.json().catch(() => null);
    if (routeMissing(res.status, json)) missing.add("undeterminable");
    return res.ok;
  } catch {
    return false;
  }
}

export function markUndeterminable(orgId: string, videoId: string, reason: UndeterminableReason): Promise<Outcome<unknown>> {
  return outcome("undeterminable", () => api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/undeterminable", { ...path(orgId, videoId), body: { reason } }));
}

/** «Passt»: the suggested court is kept as it is. */
export async function confirmCourt(orgId: string, videoId: string): Promise<boolean> {
  const { error } = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/confirm", path(orgId, videoId));
  return !error;
}

export type SaveVia = "clicks" | "points";

/**
 * Save the court from the clicks: the line-click endpoint; only where the API lacks it, the
 * points endpoint, with the clicked named points as they are (points only) or the locally fitted
 * court as points (line clicks, only when the fit passed the server's thresholds: `fitted`).
 */
export async function saveCourt(
  orgId: string,
  videoId: string,
  clicks: Clicks,
  fitted: Homography | null,
  model: CourtModel,
  space: Space = "panorama",
  frameMs = 0,
): Promise<Outcome<{ via: SaveVia }>> {
  const lines = Object.fromEntries(Object.entries(clicks.lines).filter(([, l]) => l.length > 0));
  const r = await saveClicks(orgId, videoId, { space, frame_ms: frameMs, lines, points: clicks.points });
  if (r.kind !== "missing") return r.kind === "ok" ? { kind: "ok", value: { via: "clicks" } } : r;
  const named = Object.entries(clicks.points).flatMap(([name, image]) => (model.points[name] ? [{ image, court: model.points[name]! }] : []));
  const points = Object.keys(lines).length === 0 && named.length >= 4 ? named : fitted ? courtAsPoints(fitted, clicks) : null;
  if (!points) return { kind: "refused", problem: { code: "clicks-too-few" } };
  const p = await outcome(null, () => api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration", { ...path(orgId, videoId), body: { space, frame_ms: frameMs, points } }));
  return p.kind === "ok" ? { kind: "ok", value: { via: "points" } } : p;
}

// ---- the court's state, the suggestion, the last clicks ------------------------------------

type Analysis = Schemas["AnalysisOut"];

/** A court to look at before clicking: from an earlier video of the same hall, or found
 * automatically. «Passt» keeps it (confirm). */
export interface Suggestion {
  source: "hall" | "auto";
  homography: Homography;
  imageSize: [number, number];
  space: Space;
  fromVideoId?: string;
  /** the kickoff of the match the hall's court comes from (for «Spiel vom 14. Nov.») */
  kickoffAt?: string;
  /** the hall's name */
  label?: string;
}

/** «updating»: a court the coach clicked is being applied (its analysis runs); «undeterminable»:
 * the coach said the court cannot be set on this video (clicking later undoes it). */
export type CalibrationState = NonNullable<Analysis["calibration_state"]>;

/** The court's state: the API's field, or derived from the older fields where it has none. */
export function calibrationState(a: Analysis): CalibrationState {
  if (a.calibration_state) return a.calibration_state;
  if (a.needs_calibration || !a.calibration) return "missing";
  if (a.calibration.source === "user_correction" || courtFromHallSure(a)) return "confirmed";
  return "suggested";
}

/** The suggested court, if there is one to show on the hall image. Its source: the API's field,
 * else what the court itself says (carried over from the hall: calibration_info method «hall»;
 * otherwise found automatically). */
export function suggestionOf(a: Analysis): Suggestion | null {
  if (calibrationState(a) !== "suggested") return null;
  const s = a.calibration_suggestion;
  if (s) {
    return {
      source: s.source,
      homography: s.homography,
      imageSize: s.image_size,
      space: s.space ?? "panorama",
      fromVideoId: s.from_video_id ?? undefined,
      kickoffAt: s.from_kickoff_at ?? undefined,
      label: a.hall?.name ?? undefined,
    };
  }
  // no suggestion field (an older API): the court of the analysis is the suggestion
  const cal = a.calibration;
  if (!cal) return null;
  const info = (a.calibration_info ?? {}) as { reference_video_id?: string };
  const hall = courtFromHall(a);
  return {
    source: hall ? "hall" : "auto",
    homography: cal.homography,
    imageSize: [cal.image_size[0]!, cal.image_size[1]!],
    space: "panorama",
    fromVideoId: hall ? info.reference_video_id : undefined,
    label: hall ? (a.hall?.name ?? undefined) : undefined,
  };
}

/** The coach's last clicks on the hall image, to edit them again (court_clicks); only names the
 * court model knows. */
export function lastClicks(a: Analysis, model: CourtModel): Clicks | null {
  const c = a.court_clicks;
  if (!c || (c.space ?? "panorama") !== "panorama") return null;
  const lines = Object.fromEntries(Object.entries(c.lines ?? {}).filter(([n, l]) => n in model.lines && Array.isArray(l) && l.length > 0 && l.every(isPt))) as Record<string, Pt[]>;
  const points = Object.fromEntries(Object.entries(c.points ?? {}).filter(([n, p]) => n in model.points && isPt(p))) as Record<string, Pt>;
  return Object.keys(lines).length || Object.keys(points).length ? { lines, points } : null;
}

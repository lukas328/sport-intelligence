/**
 * The API calls of the court calibration dialog, in one place.
 *
 * Line clicks have their own endpoints: GET calibration/court-model, POST .../calibration/clicks
 * and .../clicks/check, and the analysis fields calibration_state and court_clicks. Each call is
 * feature-detected: an endpoint that answers 404 is remembered as missing for this page, and the
 * dialog falls back to what works without it (the local court model and fit, saving the fitted
 * court as points on the hall image, «Passt» via confirm, no «Nicht bestimmbar» button).
 * The types below mirror the API's schemas (CourtClicksIn, CourtClicksOut, CourtModelOut); once
 * the generated api-client carries them, they can give way to Schemas[...].
 */
import type { Schemas } from "@handball/api-client";
import { api } from "@/lib/client";
import { courtAsPoints, type ClickRef, type Clicks, type CourtModel, type Pt } from "@/lib/court-fit";
import { courtFromHall, courtFromHallSure } from "@/lib/match-workflow";
import type { Homography } from "@/lib/spotlight";

export type Space = "panorama" | "frame";

/** CourtClicksIn: the body of the check and save calls for line clicks. */
export interface ClicksBody {
  space: Space;
  frame_ms: number;
  lines: Record<string, Pt[]>;
  points: Record<string, Pt>;
}

/** A click the server left out as off the line (CourtClicksOut.dropped). */
export interface DroppedClick {
  kind: "point" | "line";
  name: string;
  index: number | null;
}

/** CourtClicksOut: the court through the clicks. */
export interface ServerFit {
  homography: Homography;
  image_size: [number, number];
  residual_px: { median: number; max: number };
  dropped: DroppedClick[];
  /** px per click as the request listed them; null: a dropped click */
  per_click_px?: { lines: Record<string, (number | null)[]>; points: Record<string, number> };
}

export interface ClickProblem {
  /** clicks-too-few, clicks-disagree, clicks-unknown, no-hall-image (409), or another code */
  code: string;
  detail?: string;
  /** clicks-disagree: the click that agrees least, and the median */
  worst?: DroppedClick & { px?: number };
  median_px?: number;
}

export type Outcome<T> =
  | { kind: "ok"; value: T }
  /** the server refused the clicks (422) or the video is not ready for them (409) */
  | { kind: "refused"; problem: ClickProblem }
  /** the endpoint does not exist (yet): use the fallback */
  | { kind: "missing" }
  | { kind: "error"; status: number };

/** Why the court cannot be read: too far away, cuts in the video, something else. */
export type UndeterminableReason = "too_far" | "cut" | "other";

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

function csrf(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const m = document.cookie.split("; ").find((c) => c.startsWith("hb_csrf="));
  return m ? decodeURIComponent(m.slice("hb_csrf=".length)) : undefined;
}

/** A 404 of the router itself (no such endpoint), not a 404 problem of the API (no such video). */
function routeMissing(status: number, body: Record<string, unknown> | null): boolean {
  if (status !== 404) return false;
  const type = typeof body?.type === "string" ? body.type : "about:blank";
  return type === "about:blank";
}

function problemOf(body: Record<string, unknown> | null): ClickProblem {
  const type = typeof body?.type === "string" ? body.type : "";
  const code = typeof body?.code === "string" ? body.code : type.includes(":") ? type.slice(type.lastIndexOf(":") + 1) : type || "error";
  const w = body?.worst as Record<string, unknown> | undefined;
  const worst =
    w && (w.kind === "line" || w.kind === "point") && typeof w.name === "string"
      ? { kind: w.kind as DroppedClick["kind"], name: w.name, index: typeof w.index === "number" ? w.index : null, px: typeof w.px === "number" ? w.px : undefined }
      : undefined;
  return { code, detail: typeof body?.detail === "string" ? body.detail : undefined, worst, median_px: typeof body?.median_px === "number" ? body.median_px : undefined };
}

async function call<T>(endpoint: Endpoint, method: "GET" | "POST", url: string, body?: unknown): Promise<Outcome<T>> {
  if (missing.has(endpoint)) return { kind: "missing" };
  let res: Response;
  try {
    const token = csrf();
    res = await fetch(url, {
      method,
      credentials: "same-origin",
      headers: {
        accept: "application/json",
        ...(body !== undefined ? { "content-type": "application/json" } : {}),
        ...(method !== "GET" && token ? { "x-csrf-token": token } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    return { kind: "error", status: 0 };
  }
  const json = (await res.json().catch(() => null)) as Record<string, unknown> | null;
  if (routeMissing(res.status, json)) {
    missing.add(endpoint);
    return { kind: "missing" };
  }
  if (res.status === 422 || res.status === 409) return { kind: "refused", problem: problemOf(json) };
  if (!res.ok) return { kind: "error", status: res.status };
  return { kind: "ok", value: json as T };
}

const videoUrl = (orgId: string, videoId: string, path: string) => `/v1/orgs/${orgId}/videos/${videoId}/calibration${path}`;

const isPt = (p: unknown): p is Pt => Array.isArray(p) && p.length === 2 && p.every((v) => typeof v === "number" && Number.isFinite(v));

/** The court model the API fits with; null while it serves none (use LOCAL_COURT_MODEL). */
export async function fetchCourtModel(orgId: string): Promise<CourtModel | null> {
  const r = await call<{ lines?: Record<string, { kind?: string; court?: unknown }>; points?: Record<string, unknown> }>("court-model", "GET", `/v1/orgs/${orgId}/calibration/court-model`);
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
  return call("clicks/check", "POST", videoUrl(orgId, videoId, "/clicks/check"), body);
}

/** Save the clicks as the court (a correction; the analysis runs again; later videos of the
 * hall get it offered). */
export function saveClicks(orgId: string, videoId: string, body: ClicksBody): Promise<Outcome<ServerFit & { job_id: string }>> {
  return call("clicks", "POST", videoUrl(orgId, videoId, "/clicks"), body);
}

/** The dropped clicks of the server as the dialog names clicks. */
export function droppedRefs(d: DroppedClick[]): ClickRef[] {
  return d.map((x): ClickRef => (x.kind === "point" ? { kind: "point", name: x.name } : { kind: "line", name: x.name, index: x.index ?? 0 }));
}

/** Whether «nicht bestimmbar» can be saved: a GET on the POST endpoint answers 405 once it exists. */
export async function canMarkUndeterminable(orgId: string, videoId: string): Promise<boolean> {
  if (missing.has("undeterminable")) return false;
  try {
    const res = await fetch(videoUrl(orgId, videoId, "/undeterminable"), { credentials: "same-origin", headers: { accept: "application/json" } });
    if (res.status === 405) return true;
    const json = (await res.json().catch(() => null)) as Record<string, unknown> | null;
    if (routeMissing(res.status, json)) missing.add("undeterminable");
    return res.ok;
  } catch {
    return false;
  }
}

export function markUndeterminable(orgId: string, videoId: string, reason: UndeterminableReason): Promise<Outcome<unknown>> {
  return call("undeterminable", "POST", videoUrl(orgId, videoId, "/undeterminable"), { reason });
}

/** «Passt»: the suggested court is kept as it is (existing endpoint). */
export async function confirmCourt(orgId: string, videoId: string): Promise<boolean> {
  const { error } = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/confirm", { params: { path: { org_id: orgId, video_id: videoId } } });
  return !error;
}

/** Named court points on the hall image (existing endpoint). */
async function savePoints(orgId: string, videoId: string, points: { image: Pt; court: Pt }[], space: Space, frameMs: number): Promise<Outcome<unknown>> {
  const { error, response } = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration", {
    params: { path: { org_id: orgId, video_id: videoId } },
    body: { space, frame_ms: frameMs, points },
  });
  if (!error) return { kind: "ok", value: null };
  if (response.status === 422 || response.status === 409) return { kind: "refused", problem: problemOf(error as Record<string, unknown>) };
  return { kind: "error", status: response.status };
}

export type SaveVia = "clicks" | "points";

/**
 * Save the court from the clicks: the line-click endpoint when the API has it; otherwise the
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
  const p = await savePoints(orgId, videoId, points, space, frameMs);
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
export type CalibrationState = "confirmed" | "suggested" | "missing" | "updating" | "undeterminable";

interface CalibrationFields {
  calibration_state?: CalibrationState;
  /** the coach's latest line clicks, to edit them again */
  court_clicks?: Partial<ClicksBody> | null;
  /** with «suggested»: the proposed court and where it comes from */
  calibration_suggestion?: { source: "hall" | "auto"; from_video_id?: string | null; from_kickoff_at?: string | null; homography: Homography; image_size: [number, number]; space?: Space } | null;
}

/** The court's state: the API's field, or derived from the older fields where it has none. */
export function calibrationState(a: Analysis): CalibrationState {
  const f = a as Analysis & CalibrationFields;
  if (f.calibration_state) return f.calibration_state;
  if (a.needs_calibration || !a.calibration) return "missing";
  if (a.calibration.source === "user_correction" || courtFromHallSure(a)) return "confirmed";
  return "suggested";
}

/** The suggested court, if there is one to show on the hall image. Its source: the API's field
 * once there is one, else what the court itself says (carried over from the hall: calibration_info
 * method «hall»; otherwise found automatically). */
export function suggestionOf(a: Analysis): Suggestion | null {
  const f = a as Analysis & CalibrationFields;
  if (calibrationState(a) !== "suggested") return null;
  const s = f.calibration_suggestion;
  if (s) return { source: s.source, homography: s.homography, imageSize: s.image_size, space: s.space ?? "panorama", fromVideoId: s.from_video_id ?? undefined, kickoffAt: s.from_kickoff_at ?? undefined, label: a.hall?.name ?? undefined };
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
  const c = (a as Analysis & CalibrationFields).court_clicks;
  if (!c || (c.space ?? "panorama") !== "panorama") return null;
  const lines = Object.fromEntries(Object.entries(c.lines ?? {}).filter(([n, l]) => n in model.lines && Array.isArray(l) && l.length > 0 && l.every(isPt)));
  const points = Object.fromEntries(Object.entries(c.points ?? {}).filter(([n, p]) => n in model.points && isPt(p)));
  return Object.keys(lines).length || Object.keys(points).length ? { lines, points } : null;
}

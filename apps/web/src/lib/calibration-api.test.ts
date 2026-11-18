import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Schemas } from "@handball/api-client";
import type { Clicks } from "./court-fit";
import { HALL_H, project } from "./synthetic-hall";

// one fake API for the whole file (the typed client keeps the fetch it was made with)
type Reply = { status: number; body?: unknown };
let routes: Record<string, Reply> = {};
const seen: { method: string; path: string; body: unknown }[] = [];
const fake = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
  const req = input instanceof Request ? input : new Request(new URL(String(input), "http://localhost"), init);
  const path = new URL(req.url).pathname;
  const text = await req.text();
  seen.push({ method: req.method, path, body: text ? JSON.parse(text) : undefined });
  const r = routes[`${req.method} ${path}`] ?? { status: 404, body: { type: "about:blank", title: "Not Found", status: 404, detail: "Not Found" } };
  return new Response(r.body === undefined ? null : JSON.stringify(r.body), { status: r.status, headers: { "content-type": "application/json" } });
});
vi.stubGlobal("fetch", fake);
const apiModule = await import("./calibration-api");
const { saveCourt, checkClicks, canMarkUndeterminable, fetchCourtModel, calibrationState, suggestionOf, lastClicks, resetFeatureDetection, isMissing, droppedRefs } = apiModule;
const { LOCAL_COURT_MODEL, fitClicks } = await import("./court-fit");

const V = "/v1/orgs/o/videos/v/calibration";
const at = (x: number, y: number) => project(HALL_H, x, y);
const CLICKS: Clicks = {
  points: {},
  lines: { side_near: [at(5, 0), at(18, 0), at(33, 0)], side_far: [at(7, 20), at(20, 20), at(32, 20)], goal_left: [at(0, 4), at(0, 15)], centre: [at(20, 3), at(20, 17)] },
};

beforeEach(() => {
  routes = {};
  seen.length = 0;
  resetFeatureDetection();
});

describe("calibration API with feature detection", () => {
  it("saves line clicks through /clicks when the API has it", async () => {
    routes[`POST ${V}/clicks`] = { status: 202, body: { job_id: "j", homography: HALL_H, image_size: [1280, 720], residual_px: { median: 0.4, max: 1 }, dropped: [], per_click_px: { lines: {}, points: {} } } };
    const fit = fitClicks(CLICKS, [1280, 720]);
    const r = await saveCourt("o", "v", CLICKS, fit.homography, LOCAL_COURT_MODEL);
    expect(r).toEqual({ kind: "ok", value: { via: "clicks" } });
    expect(seen.map((s) => s.path)).toEqual([`${V}/clicks`]);
    expect(seen[0]!.body).toMatchObject({ space: "panorama", frame_ms: 0, lines: CLICKS.lines, points: {} });
  });

  it("falls back to the points endpoint with the fitted court when /clicks is missing", async () => {
    routes[`POST ${V}`] = { status: 202, body: { job_id: "j" } };
    const fit = fitClicks(CLICKS, [1280, 720]);
    const r = await saveCourt("o", "v", CLICKS, fit.homography, LOCAL_COURT_MODEL);
    expect(r).toEqual({ kind: "ok", value: { via: "points" } });
    const body = seen.find((s) => s.path === V)!.body as { points: { image: [number, number]; court: [number, number] }[]; space: string };
    expect(body.space).toBe("panorama");
    expect(body.points.length).toBeGreaterThanOrEqual(4);
    // the points lie on the hall's court
    for (const p of body.points) {
      const q = project(HALL_H, p.court[0], p.court[1]);
      expect(Math.hypot(q[0] - p.image[0], q[1] - p.image[1])).toBeLessThan(0.5);
    }
    expect(isMissing("clicks")).toBe(true);
    // asked once per page: the next save goes straight to the points
    await saveCourt("o", "v", CLICKS, fit.homography, LOCAL_COURT_MODEL);
    expect(seen.filter((s) => s.path === `${V}/clicks`)).toHaveLength(1);
  });

  it("sends named points as they are when there are no line clicks", async () => {
    routes[`POST ${V}`] = { status: 202, body: { job_id: "j" } };
    const points = { corner_bl: at(0, 0), corner_tl: at(0, 20), center_bottom: at(20, 0), center_top: at(20, 20) };
    await saveCourt("o", "v", { points, lines: {} }, null, LOCAL_COURT_MODEL);
    const body = seen.find((s) => s.path === V)!.body as { points: { image: number[]; court: number[] }[] };
    expect(body.points).toContainEqual({ image: points.corner_tl, court: [0, 20] });
  });

  it("reads a refusal: code, worst click and median", async () => {
    routes[`POST ${V}/clicks/check`] = {
      status: 422,
      body: { type: "urn:handball-platform:problem:clicks-disagree", title: "Unprocessable Content", status: 422, detail: "the clicks do not agree", median_px: 7.5, worst: { kind: "line", name: "six_left", index: 1, px: 31 } },
    };
    const r = await checkClicks("o", "v", { space: "panorama", frame_ms: 0, ...CLICKS });
    expect(r).toEqual({ kind: "refused", problem: { code: "clicks-disagree", detail: "the clicks do not agree", median_px: 7.5, worst: { kind: "line", name: "six_left", index: 1, px: 31 } } });
    routes[`POST ${V}/clicks/check`] = { status: 409, body: { type: "urn:handball-platform:problem:no-hall-image", title: "Conflict", status: 409 } };
    expect(await checkClicks("o", "v", { space: "panorama", frame_ms: 0, ...CLICKS })).toMatchObject({ kind: "refused", problem: { code: "no-hall-image" } });
    expect(droppedRefs([{ kind: "line", name: "side_far", index: 2 }, { kind: "point", name: "corner_tl", index: null }])).toEqual([
      { kind: "line", name: "side_far", index: 2 },
      { kind: "point", name: "corner_tl" },
    ]);
  });

  it("tells a missing endpoint from a 404 of the API", async () => {
    routes[`POST ${V}/clicks/check`] = { status: 404, body: { type: "urn:handball-platform:problem:not-found", title: "Not Found", status: 404 } };
    expect((await checkClicks("o", "v", { space: "panorama", frame_ms: 0, ...CLICKS })).kind).toBe("error");
    expect(isMissing("clicks/check")).toBe(false);
  });

  it("offers «nicht bestimmbar» only once the endpoint answers", async () => {
    expect(await canMarkUndeterminable("o", "v")).toBe(false);
    resetFeatureDetection();
    routes[`GET ${V}/undeterminable`] = { status: 405, body: { type: "about:blank", title: "Method Not Allowed", status: 405 } };
    expect(await canMarkUndeterminable("o", "v")).toBe(true);
  });

  it("uses the API's court model when it serves one", async () => {
    expect(await fetchCourtModel("o")).toBeNull();
    routes["GET /v1/orgs/o/calibration/court-model"] = { status: 200, body: { lines: { side_near: { kind: "line", court: [[0, 0], [40, 0]] }, bad: { kind: "x", court: [] } }, points: { corner_bl: [0, 0], nope: "x" } } };
    resetFeatureDetection();
    expect(await fetchCourtModel("o")).toEqual({ lines: { side_near: { kind: "line", court: [[0, 0], [40, 0]] } }, points: { corner_bl: [0, 0] } });
  });
});

describe("the court's state and suggestion", () => {
  const base = {
    status: "ready",
    calibration: { homography: HALL_H, image_size: [1280, 720], confidence: 0.7, reprojection_px: 2, source: "heuristic", created_at: "2026-11-14T18:00:00Z" },
    calibration_info: { method: "hall", reference_video_id: "earlier" },
    camera: "moving",
    panorama: { width: 1280, height: 720 },
    hall: { name: "Sporthalle Kieselgrund", source: "match", calibrated_videos: 1 },
    needs_calibration: false,
  } as unknown as Schemas["AnalysisOut"];

  it("derives the state from the older fields while the API has none", () => {
    expect(calibrationState(base)).toBe("suggested");
    expect(suggestionOf(base)).toMatchObject({ source: "hall", fromVideoId: "earlier", label: "Sporthalle Kieselgrund" });
    expect(calibrationState({ ...base, needs_calibration: true })).toBe("missing");
    expect(calibrationState({ ...base, calibration: { ...base.calibration!, source: "user_correction" } })).toBe("confirmed");
    expect(suggestionOf({ ...base, calibration_info: { method: "goals" } })).toMatchObject({ source: "auto" });
  });

  it("takes the API's state, suggestion and last clicks", () => {
    const a = {
      ...base,
      calibration_state: "suggested",
      calibration_suggestion: { source: "hall", homography: HALL_H, image_size: [1280, 720], space: "panorama", from_video_id: "v0", from_kickoff_at: "2026-11-14T18:00:00Z" },
      court_clicks: { space: "panorama", frame_ms: 0, lines: { side_near: [[1, 2], [3, 4]], nonsense: [[1, 1]] }, points: { corner_bl: [5, 6] } },
    } as unknown as Schemas["AnalysisOut"];
    expect(suggestionOf(a)).toMatchObject({ source: "hall", fromVideoId: "v0", kickoffAt: "2026-11-14T18:00:00Z" });
    expect(lastClicks(a, LOCAL_COURT_MODEL)).toEqual({ lines: { side_near: [[1, 2], [3, 4]] }, points: { corner_bl: [5, 6] } });
    expect(calibrationState({ ...a, calibration_state: "undeterminable" } as unknown as Schemas["AnalysisOut"])).toBe("undeterminable");
    expect(suggestionOf({ ...a, calibration_state: "confirmed" } as unknown as Schemas["AnalysisOut"])).toBeNull();
  });
});

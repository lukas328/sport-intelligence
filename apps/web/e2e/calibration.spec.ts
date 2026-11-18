import { expect, test, type Page } from "@playwright/test";
import { fitClicks, type Clicks } from "../src/lib/court-fit";
import { HALL_H, project } from "../src/lib/synthetic-hall";

// The court calibration dialog on its component page (/dev/kalibrierung: a drawn hall image, no
// video needed). The API answers are recorded here: once as the API has them (clicks, check,
// court model, nicht bestimmbar), once without them (404: the dialog falls back to points).
// Run against a dev server, or a build with HB_DEV_PAGES=1.

type Call = { method: string; path: string; body: unknown };

async function fakeApi(page: Page, withLineEndpoints: boolean): Promise<Call[]> {
  const calls: Call[] = [];
  await page.route("**/v1/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    calls.push({ method: req.method(), path, body: req.postDataJSON() });
    const json = (status: number, body: unknown) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path.endsWith("/calibration/confirm")) return json(200, { calibration_id: "c", source: "user_correction" });
    if (/\/calibration$/.test(path) && req.method() === "POST") return json(202, { job_id: "j" });
    if (withLineEndpoints) {
      if (path.endsWith("/clicks/check") || path.endsWith("/calibration/clicks")) {
        // the server's fit, played by the same method (lib/court-fit: the API's thresholds)
        const f = fitClicks(req.postDataJSON() as Clicks, [1280, 720]);
        if (f.status !== "ok") {
          const w = f.worst;
          return json(422, { type: `urn:handball-platform:problem:clicks-${f.status === "disagree" ? "disagree" : "too-few"}`, title: "Unprocessable Content", status: 422, median_px: f.medianPx, worst: w && { kind: w.kind, name: w.name, index: w.kind === "line" ? w.index : null, px: w.px } });
        }
        const fit = { homography: f.homography, image_size: [1280, 720], residual_px: { median: f.medianPx, max: f.maxPx }, dropped: f.dropped.map((d) => ({ kind: d.kind, name: d.name, index: d.kind === "line" ? d.index : null })), per_click_px: { lines: {}, points: {} } };
        return path.endsWith("/check") ? json(200, fit) : json(202, { ...fit, job_id: "j" });
      }
      if (path.endsWith("/calibration/undeterminable")) return req.method() === "GET" ? json(405, { type: "about:blank", title: "Method Not Allowed", status: 405 }) : route.fulfill({ status: 204 });
    }
    return json(404, { type: "about:blank", title: "Not Found", status: 404, detail: "Not Found" });
  });
  return calls;
}

/** Screen position of a court point (metres) in the dialog's picture. */
async function screenOf(page: Page, x: number, y: number): Promise<[number, number]> {
  const stage = page.getByTestId("calibration-stage");
  const box = (await stage.boundingBox())!;
  const [vx, vy, vw, vh] = (await stage.getAttribute("viewBox"))!.split(" ").map(Number) as [number, number, number, number];
  const s = Math.min(box.width / vw, box.height / vh);
  const [u, v] = project(HALL_H, x, y);
  return [box.x + (box.width - vw * s) / 2 + (u - vx) * s, box.y + (box.height - vh * s) / 2 + (v - vy) * s];
}

/** The quickest set: both sidelines (three taps each, the next line follows by itself), the left
 * goal line and the centre line (two taps each); a tap lands a few pixels beside the line. */
async function clickTheLines(page: Page, touch: boolean): Promise<number> {
  let taps = 0;
  const tap = async (x: number, y: number, dx: number, dy: number) => {
    const [sx, sy] = await screenOf(page, x, y);
    if (touch) await page.touchscreen.tap(sx + dx, sy + dy);
    else await page.mouse.click(sx + dx, sy + dy);
    taps++;
  };
  for (const x of [5, 18, 33]) await tap(x, 0, 0, 2);
  await expect(page.getByTestId("line-side_far")).toHaveAttribute("aria-pressed", "true");
  for (const x of [7, 20, 32]) await tap(x, 20, 0, -2);
  await expect(page.getByTestId("line-goal_left")).toHaveAttribute("aria-pressed", "true");
  for (const y of [4, 15]) await tap(0, y, 2, 0);
  await page.getByTestId("line-centre").click();
  taps++;
  for (const y of [3, 17]) await tap(20, y, -2, 0);
  return taps;
}

test("the court from this hall: one tap «Passt»", async ({ page }) => {
  const calls = await fakeApi(page, false);
  await page.goto("/dev/kalibrierung?state=hall");
  const dialog = page.getByRole("dialog", { name: "Passt das Spielfeld?" });
  await expect(dialog).toBeVisible();
  await expect(page.getByTestId("suggestion-source")).toHaveText("Feld aus dieser Halle: Sporthalle Kieselgrund");
  await expect(page.getByTestId("overlay-suggest")).toBeAttached();
  // without its endpoint there is no «Nicht bestimmbar»
  await expect(page.getByTestId("calibration-undeterminable")).toHaveCount(0);
  await page.getByTestId("calibration-confirm").click();
  await expect(dialog).toBeHidden();
  expect(calls.filter((c) => c.method === "POST").map((c) => c.path)).toEqual(["/v1/orgs/demo/videos/demo/calibration/confirm"]);
});

test("line mode with the API's line endpoints: the live court, the server's check, saved as clicks", async ({ page }, info) => {
  const calls = await fakeApi(page, true);
  await page.goto("/dev/kalibrierung?state=auto");
  await expect(page.getByTestId("suggestion-source")).toHaveText("Automatischer Vorschlag");
  const started = Date.now();
  await page.getByTestId("calibration-correct").click();
  const save = page.getByTestId("calibration-save");
  await expect(save).toBeDisabled();
  const taps = 1 + (await clickTheLines(page, info.project.name === "mobile"));
  await expect(page.getByTestId("overlay-fit")).toBeAttached();
  await expect(page.getByTestId("calibration-quality-text")).toContainText("Passt");
  await expect(save).toBeEnabled();
  // the server checks the clicks once they are enough (after a pause, not on every tap)
  await expect.poll(() => calls.filter((c) => c.path.endsWith("/clicks/check")).length).toBeGreaterThan(0);
  expect(calls.filter((c) => c.path.endsWith("/clicks/check")).length).toBeLessThanOrEqual(2);
  await page.screenshot({ path: info.outputPath("calibration-lines.png") });
  await save.click();
  await expect(page.getByTestId("calibration-dialog")).toBeHidden();
  const seconds = (Date.now() - started) / 1000;
  const sent = calls.find((c) => c.path.endsWith("/calibration/clicks"))!.body as { space: string; lines: Record<string, number[][]>; points: object };
  expect(sent.space).toBe("panorama");
  expect(Object.keys(sent.lines).sort()).toEqual(["centre", "goal_left", "side_far", "side_near"]);
  // the taps snapped onto the painted lines: every click within a pixel of its line
  for (const [, y] of sent.lines.side_near!) expect(Math.abs(y! - project(HALL_H, 0, 0)[1])).toBeLessThan(1.5);
  expect(calls.some((c) => c.path === "/v1/orgs/demo/videos/demo/calibration")).toBe(false);
  test.info().annotations.push({ type: "taps", description: `${taps + 1} taps, ${seconds.toFixed(1)} s` });
});

test("without the line endpoints the fitted court is saved as points", async ({ page }, info) => {
  const calls = await fakeApi(page, false);
  await page.goto("/dev/kalibrierung?state=missing");
  await expect(page.getByRole("dialog", { name: "Spielfeld markieren" })).toBeVisible();
  await clickTheLines(page, info.project.name === "mobile");
  await expect(page.getByTestId("calibration-save")).toBeEnabled();
  await page.getByTestId("calibration-save").click();
  await expect(page.getByTestId("calibration-dialog")).toBeHidden();
  const body = calls.find((c) => c.path === "/v1/orgs/demo/videos/demo/calibration")!.body as { space: string; points: { image: number[]; court: number[] }[] };
  expect(body.space).toBe("panorama");
  expect(body.points.length).toBeGreaterThanOrEqual(4);
  for (const p of body.points) {
    const [u, v] = project(HALL_H, p.court[0]!, p.court[1]!);
    expect(Math.hypot(u - p.image[0]!, v - p.image[1]!)).toBeLessThan(2);
  }
});

test("a click on the wrong line is named, undo takes it back; «Nicht bestimmbar» with a reason", async ({ page }, info) => {
  const calls = await fakeApi(page, true);
  await page.goto("/dev/kalibrierung?state=missing");
  await clickTheLines(page, info.project.name === "mobile");
  await expect(page.getByTestId("calibration-save")).toBeEnabled();
  // a third click «on the centre line» far beside it, snapping off: the court no longer fits
  await page.getByTestId("calibration-snap").click();
  const [sx, sy] = await screenOf(page, 26, 10);
  if (info.project.name === "mobile") await page.touchscreen.tap(sx, sy);
  else await page.mouse.click(sx, sy);
  // which of the centre line's clicks is wrong the clicks do not show: named, not saved
  await expect(page.getByTestId("calibration-hint")).toContainText("Mittellinie");
  await expect(page.getByTestId("calibration-save")).toBeDisabled();
  await page.getByTestId("calibration-undo").click();
  await expect(page.getByTestId("calibration-save")).toBeEnabled();
  // the court cannot be read after all: say so, with the reason
  await page.getByTestId("calibration-undeterminable").click();
  await page.getByTestId("skip-cut").click();
  await expect(page.getByTestId("calibration-dialog")).toBeHidden();
  expect(calls.find((c) => c.method === "POST" && c.path.endsWith("/calibration/undeterminable"))!.body).toEqual({ reason: "cut" });
});

test("keys on the desktop: 1 to 9 choose the line, Z undoes", async ({ page }, info) => {
  test.skip(info.project.name === "mobile", "keys are the desktop's");
  await fakeApi(page, false);
  await page.goto("/dev/kalibrierung?state=missing");
  await page.keyboard.press("6");
  await expect(page.getByTestId("line-six_left")).toHaveAttribute("aria-pressed", "true");
  const [sx, sy] = await screenOf(page, 6, 10);
  await page.mouse.click(sx, sy);
  await expect(page.getByTestId("line-six_left")).toHaveAccessibleName(/1 Klick/);
  await page.keyboard.press("z");
  await expect(page.getByTestId("line-six_left")).toHaveAccessibleName(/noch kein Klick/);
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("calibration-dialog")).toBeHidden();
});

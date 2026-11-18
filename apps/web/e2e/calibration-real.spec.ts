import { expect, test, type Page } from "@playwright/test";
import { MATCH_VIDEO } from "./global-setup";
import { chooseVideo, clubByHand, follow, register, uniqueEmail } from "./helpers";

// The court calibration dialog against the real API and pipeline: a synthetic clip uploaded and
// analysed, the court marked with line clicks on its hall image (court model, the server's check
// with per-click distances, saved as clicks: the analysis runs again), then opened again with
// the clicks prefilled.
test("court by line clicks on the real API: checked, saved, opened again", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(420_000);
  await register(page, uniqueEmail("court"), "Coach Linien");
  await clubByHand(page, "HC Linien");
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Rotdorn");
  await page.getByRole("button", { name: "Spiel anlegen" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("TV Rotdorn");
  await chooseVideo(page, MATCH_VIDEO);
  await expect(page.getByTestId("player").filter({ visible: true })).toBeVisible({ timeout: 180_000 });

  // the court step of the workbench, once the analysis is there
  if (await page.getByTestId("open-bench").isVisible()) await page.getByTestId("open-bench").click();
  await page.getByTestId("setup-toggle").click();
  await page.getByTestId("step-court").click();
  const mark = page.getByTestId("mark-court").first();
  await expect(mark).toBeVisible({ timeout: 240_000 });

  const calls: string[] = [];
  page.on("response", (r) => r.url().includes("/calibration") && calls.push(`${r.request().method()} ${new URL(r.url()).pathname.replace(/^.*\/calibration/, "calibration")} ${r.status()}`));
  const analysisUrl = await page.evaluate(() => performance.getEntriesByType("resource").map((e) => e.name).find((n) => /\/videos\/[^/]+\/analysis$/.test(n)) ?? null);
  expect(analysisUrl).not.toBeNull();
  const analysis = await page.evaluate(async (u) => (await fetch(u)).json(), analysisUrl!);
  const h: number[][] = (analysis.calibration_suggestion ?? analysis.calibration).homography;

  await mark.click();
  await expect(page.getByTestId("calibration-dialog")).toBeVisible();
  if (await page.getByTestId("calibration-correct").isVisible()) await page.getByTestId("calibration-correct").click();
  await expect.poll(() => calls.some((c) => c === "GET calibration/court-model 200" || c.endsWith("court-model 200"))).toBe(true);
  const checked = page.waitForResponse((r) => r.url().endsWith("/calibration/clicks/check") && r.request().method() === "POST");
  await tapLines(page, h);
  const check = await checked;
  expect(check.status()).toBe(200);
  const fit = await check.json();
  expect(fit.homography).toHaveLength(3);
  expect(Object.keys(fit.per_click_px.lines).sort()).toEqual(["centre", "goal_left", "side_far", "side_near"]);
  await expect(page.getByTestId("calibration-save")).toBeEnabled();
  const saved = page.waitForResponse((r) => r.url().endsWith("/calibration/clicks") && r.request().method() === "POST");
  await page.getByTestId("calibration-save").click();
  expect((await saved).status()).toBe(202);
  await expect(page.getByTestId("calibration-dialog")).toBeHidden();

  // the clicks stay with the video: opened again, the lines are there to edit
  await expect(mark).toBeVisible({ timeout: 240_000 });
  await mark.click();
  if (await page.getByTestId("calibration-correct").isVisible()) await page.getByTestId("calibration-correct").click();
  await expect(page.getByTestId("line-side_near")).toHaveAccessibleName(/3 Klicks/);
  await page.screenshot({ path: info.outputPath("court-real.png") });
});

async function tapLines(page: Page, h: number[][]) {
  const proj = (x: number, y: number) => {
    const w = h[2]![0]! * x + h[2]![1]! * y + h[2]![2]!;
    return [(h[0]![0]! * x + h[0]![1]! * y + h[0]![2]!) / w, (h[1]![0]! * x + h[1]![1]! * y + h[1]![2]!) / w] as const;
  };
  const tap = async (x: number, y: number) => {
    const stage = page.getByTestId("calibration-stage");
    const b = (await stage.boundingBox())!;
    const [vx, vy, vw, vh] = (await stage.getAttribute("viewBox"))!.split(" ").map(Number) as [number, number, number, number];
    const s = Math.min(b.width / vw, b.height / vh);
    const [u, v] = proj(x, y);
    await page.mouse.click(b.x + (b.width - vw * s) / 2 + (u - vx) * s, b.y + (b.height - vh * s) / 2 + (v - vy) * s);
  };
  await page.getByTestId("line-side_near").click();
  for (const x of [5, 18, 33]) await tap(x, 0);
  await page.getByTestId("calibration-next").click();
  for (const x of [7, 20, 32]) await tap(x, 20);
  await page.getByTestId("calibration-next").click();
  for (const y of [4, 15]) await tap(0, y);
  await page.getByTestId("line-centre").click();
  for (const y of [3, 17]) await tap(20, y);
}

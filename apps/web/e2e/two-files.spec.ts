import { expect, test, type Page } from "@playwright/test";
import { HALF_1, HALF_2 } from "./global-setup";
import { expectAccessible, register, uniqueEmail } from "./helpers";

/**
 * Q-VIDEO-PARTS: a coach stopped the recording at half-time and has two files. Both are chosen at
 * once; both are analysed; the match video plays both halves one after the other; the order can
 * be swapped and a file removed; the same file again is said.
 */
async function newMatch(page: Page, prefix: string): Promise<{ org: string; match: string }> {
  await register(page, uniqueEmail(prefix), "Coach Zwei Dateien");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Pause");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, org, team] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const res = await page.request.post(`/v1/orgs/${org}/teams/${team}/matches`, {
    headers: { "x-csrf-token": csrf },
    data: { opponent_name: "TV Halbzeit", opponent_kit: "#dc2626", kickoff_at: new Date(Date.now() - 86_400_000).toISOString(), score_own: 20, score_opponent: 18 },
  });
  expect(res.ok()).toBeTruthy();
  return { org: org!, match: ((await res.json()) as { id: string }).id };
}

type Graphics = { analysis: string; parts: { video_id: string; start_ms: number; analysis: string }[] };

test("two halves in two files: one match, both analysed, one video", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once; the phone layout is shot below");
  test.setTimeout(480_000);
  const { org, match } = await newMatch(page, "parts");
  await page.goto(`/app/${org}/matches/${match}?tab=video`);
  // both files at once; they go up one after the other
  await page.getByTestId("video-file").setInputFiles([HALF_2, HALF_1]);
  await expect(page.getByTestId("upload-queue-item")).toHaveCount(2);
  await expect(page.getByTestId("upload-queue-item").nth(1)).toHaveAttribute("data-status", "done", { timeout: 120_000 });
  await expect(page.getByTestId("upload-queue-item").nth(0)).toHaveAttribute("data-status", "done");

  // both analysed, each at its place on the match
  const graphics = async () => (await (await page.request.get(`/v1/orgs/${org}/matches/${match}/graphics`)).json()) as Graphics;
  await expect.poll(async () => (await graphics()).parts.map((p) => p.analysis).join(","), { timeout: 360_000, intervals: [3000] }).toBe("ready,ready");
  const g = await graphics();
  expect(g.parts[0]!.start_ms).toBe(0);
  expect(g.parts[1]!.start_ms).toBeGreaterThan(14_000);

  await page.reload();
  const list = page.getByTestId("parts");
  await expect(list.getByTestId("part-row")).toHaveCount(2);
  await expect(list).toContainText("1. Halbzeit");
  await expect(list).toContainText("2. Halbzeit");
  await expect(list.getByTestId("part-row").first()).toHaveAttribute("data-state", "ready");
  // no word like «Zeitleiste» or «Versatz»; no «nur die erste Datei»
  await expect(page.locator("body")).not.toContainText(/Zeitleiste|Versatz|nur die erste/);

  // the video plays both halves: one stream as long as both files
  const line = page.getByTestId("parts-line");
  await expect(line).toContainText("beide Halbzeiten");
  const video = page.getByTestId("video").first();
  await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => v.duration), { timeout: 60_000 }).toBeGreaterThan(28);
  await line.getByTestId("parts-jump").click();
  await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(14);
  const first = g.parts[0]!.video_id;
  const playlist = await (await page.request.get(`/v1/orgs/${org}/videos/${first}/media/hls/720p/index.m3u8`)).text();
  expect(playlist).toContain("#EXT-X-DISCONTINUITY");

  await page.setViewportSize({ width: 1280, height: 900 });
  await list.scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath("parts-desktop.png"), fullPage: false });
  await expectAccessible(page);

  // «Reihenfolge stimmt nicht? Tauschen»
  await list.getByTestId("parts-swap").click();
  await expect.poll(async () => (await graphics()).parts[0]!.video_id).not.toBe(first);
  await expect(list).toContainText("Reihenfolge von dir festgelegt");

  // the same file again: said, nothing stored twice
  await page.getByText("Weitere Datei hinzufügen").click();
  await page.getByTestId("video-file").last().setInputFiles(HALF_1);
  await expect(page.getByTestId("upload-same")).toBeVisible({ timeout: 60_000 });

  // a file removed: the other one stays and plays alone
  page.once("dialog", (d) => void d.accept());
  await list.getByTestId("part-remove").first().click();
  await page.getByRole("button", { name: "Entfernen" }).last().click();
  await expect.poll(async () => (await graphics()).parts.length).toBe(0);
  await expect(page.getByTestId("parts")).toHaveCount(0);
});

test("the list of halves on a phone", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "the phone layout");
  test.setTimeout(300_000);
  const { org, match } = await newMatch(page, "parts-phone");
  await page.goto(`/app/${org}/matches/${match}?tab=video`);
  await page.getByTestId("video-file").setInputFiles([HALF_1, HALF_2]);
  await expect(page.getByTestId("upload-queue-item").nth(1)).toHaveAttribute("data-status", "done", { timeout: 120_000 });
  await page.screenshot({ path: test.info().outputPath("upload-phone.png"), fullPage: true });
  await page.reload();
  await expect(page.getByTestId("part-row")).toHaveCount(2, { timeout: 60_000 });
  await page.getByTestId("parts").scrollIntoViewIfNeeded();
  await page.screenshot({ path: test.info().outputPath("parts-phone.png"), fullPage: false });
  // no horizontal scroll at phone width
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});

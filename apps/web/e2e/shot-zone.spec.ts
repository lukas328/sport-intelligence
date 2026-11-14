import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { MATCH_VIDEO } from "./global-setup";
import { expectAccessible, register, uniqueEmail } from "./helpers";

const DB = process.env.E2E_DATABASE_URL ?? "postgresql://handball:handball@localhost:5432/handball";

/**
 * «Von wo?» (fourth real-video test H7), on a phone: a confirmed goal asks where the shot came
 * from, one tap saves it and the next question follows; after three goals from the same place the
 * start shows a thing; a goal without a place is filled in from the start, goal by goal.
 */
test("a confirmed goal asks «Von wo?»; three from one place make a thing; the rest is filled in", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "the phone is the case: one thumb on the small court");
  test.setTimeout(300_000);
  await register(page, uniqueEmail("wurfort"), "Coach Wurfort");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Wurfort");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, org, team] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const headers = { "x-csrf-token": csrf };
  const match = await (
    await page.request.post(`/v1/orgs/${org}/teams/${team}/matches`, {
      headers,
      data: { opponent_name: "TV Ecke", kickoff_at: new Date(Date.now() - 86_400_000).toISOString(), kit_opponent: "#f2f2f2" },
    })
  ).json();
  await page.goto(`/app/${org}/matches/${match.id}?tab=video`);
  await page.getByTestId("video-file").setInputFiles(MATCH_VIDEO);
  await expect
    .poll(async () => (await (await page.request.get(`/v1/orgs/${org}/matches/${match.id}/graphics`)).json()).analysis, { timeout: 240_000, intervals: [2000] })
    .toBe("ready");
  const video = (await (await page.request.get(`/v1/orgs/${org}/matches/${match.id}`)).json()).videos[0].id as string;
  // three goal moments of ours, the strongest rate, 12 s apart: no clip holds an earlier one
  const rows = [1000, 13000, 25000].map((ms, i) => `('${randomUUID()}', '${org}', '${match.id}', '${video}', 'goal', ${ms + 1500}, ${ms}, ${Math.max(0, ms - 3000)}, ${ms + 3000}, ${3 - i * 0.1}, 1, ${i}, 'open', 'own')`).join(", ");
  execFileSync("psql", [DB, "-qc", `INSERT INTO goal_candidates (id, organization_id, match_id, video_asset_id, kind, t_ms, goal_ms, start_ms, end_ms, score, rate, rank, status, suggested_side) VALUES ${rows}`]);

  await page.goto(`/app/${org}/matches/${match.id}/check`);
  await expect(page.getByText(/^Frage 1 von \d+$/)).toBeVisible({ timeout: 30_000 });
  // question 1 has no «Zurück» (H10)
  await expect(page.getByTestId("check-back")).toHaveCount(0);
  await page.getByRole("button", { name: "Passt" }).click();
  await page.getByRole("button", { name: "Jetzt ist Anwurf" }).click();
  for (let n = 0; n < 3; n++) {
    await page.getByRole("button", { name: "Tor HC Wurfort" }).click();
    // the goal is saved, the same question asks where from, the video stays above
    const step = page.getByTestId("spot-step");
    await expect(step).toContainText("Tor HC Wurfort ist gespeichert.");
    await expect(step.getByRole("heading", { name: "Von wo?" })).toBeVisible();
    // the clip runs on in a loop while the coach taps, with «Anhalten» beside «Von wo?» (V7)
    await expect(page.getByTestId("spot-pause")).toHaveText("Anhalten");
    const at = () => page.getByTestId("video").evaluate((v: HTMLVideoElement) => v.currentTime);
    const t0 = await at();
    await expect.poll(at, { timeout: 15_000 }).toBeGreaterThan(t0 + 0.5);
    // no estimate is offered as a suggestion (V2)
    await expect(page.getByTestId("spot-picker")).not.toContainText("Vorschlag");
    if (n === 0) {
      // one screen on a phone: the bottom of the video and «Weiss nicht» are in view together, no scrolling
      for (const size of [{ width: 390, height: 844 }, { width: 360, height: 740 }]) {
        await page.setViewportSize(size);
        await expect(page.getByTestId("spot-unknown")).toBeVisible();
        await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
        const video = (await page.getByTestId("video").boundingBox())!;
        const unknown = (await page.getByTestId("spot-unknown").boundingBox())!;
        expect(video.y).toBeGreaterThanOrEqual(0);
        expect(video.y + video.height).toBeLessThanOrEqual(size.height);
        expect(unknown.y + unknown.height).toBeLessThanOrEqual(size.height);
      }
      await expectAccessible(page);
      // every place is a target of at least 44 px for a thumb
      for (const z of ["la", "kr", "ra", "rl", "rm", "rr"]) {
        const box = (await page.getByTestId(`spot-zone-${z}`).boundingBox())!;
        expect(Math.min(box.width, box.height)).toBeGreaterThanOrEqual(44);
      }
    }
    // one tap saves and goes on: no «Weiter»
    await page.getByTestId("spot-zone-rl").click();
    await expect(page.getByTestId("spot-step")).toHaveCount(0);
  }
  await expect(page.getByTestId("check-answered")).toContainText("Wurfort: Rückraum links");
  await expect(page.getByTestId("check-failed")).toHaveCount(0);
  // «Beantwortet» comes from the saved answers: still there after a reload, with «Wurfort ändern» (V5)
  await page.reload();
  await expect(page.getByTestId("check-answered")).toContainText("Wurfort: Rückraum links", { timeout: 30_000 });
  await expect(page.getByTestId("check-spot-change")).toHaveCount(3);
  // an opponent goal confirmed without a place (as in a match before «Von wo?»)
  const old = await page.request.post(`/v1/orgs/${org}/matches/${match.id}/events`, { headers, data: { type: "shot", side: "opponent", outcome: "goal", t_ms: 8000 } });
  expect(old.status()).toBe(201);

  // the start: one thing from three goals from the left back court, at once, «bisher»
  await page.goto(`/app/${org}/teams/${team}/matches`);
  const things = page.getByTestId("three-things");
  await expect(things).toBeVisible({ timeout: 30_000 });
  await expect(things).toContainText("Rückraum links");
  const status = page.getByTestId("spot-status");
  await expect(status).toContainText("Ein Ding bisher.");
  await expect(status).toContainText("Bei 1 Tor fehlt, von wo geworfen wurde.");
  // every goal stays reachable under the thing, folded (V4)
  await page.getByTestId("all-goals").locator("summary").click();
  await expect(page.getByTestId("all-goals").getByTestId("video-goal")).toHaveCount(4);

  // «nachtragen»: only «Von wo?», with the count
  await status.getByTestId("spot-fill").click();
  await expect(page.getByTestId("spot-fill-view")).toBeVisible();
  await expect(page.getByTestId("spot-step")).toContainText("1 von 1");
  await expect(page.getByTestId("spot-step")).toContainText("Tor TV Ecke");
  await expectAccessible(page);
  await page.getByTestId("spot-zone-la").click();
  await expect(page.getByTestId("spot-fill-done")).toContainText("Alle Wurforte sind eingetragen.");
  await page.getByTestId("spot-fill-to-match").click();
  await expect(page.getByTestId("spot-status")).toHaveCount(0);
});

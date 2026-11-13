import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";
import { MATCH_VIDEO } from "./global-setup";
import { register, uniqueEmail } from "./helpers";

// the local stack's and CI's database (docker compose): the goal candidates the recognition would
// find in a real hall video, which the 30 s synthetic clip does not give
const DB = process.env.E2E_DATABASE_URL ?? "postgresql://handball:handball@localhost:5432/handball";

/**
 * Real-video test, the normal case: the analysis finds no goal by itself, only candidates. After
 * the court, the throw-off and three confirmed goals the coach sees a result, the course, the
 * goals as scenes and positions on the tactics camera (E01, E02, E10).
 */
test("no goal found by the analysis: after Prüfen the result, course, goals and positions stand", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(300_000);
  await register(page, uniqueEmail("echt"), "Coach Echt");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Echt");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, org, team] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const match = await (
    await page.request.post(`/v1/orgs/${org}/teams/${team}/matches`, {
      headers: { "x-csrf-token": csrf },
      data: { opponent_name: "TV Kandidat", kickoff_at: new Date(Date.now() - 86_400_000).toISOString(), kit_opponent: "#f2f2f2" },
    })
  ).json();
  await page.goto(`/app/${org}/matches/${match.id}?tab=video`);
  await page.getByTestId("video-file").setInputFiles(MATCH_VIDEO);
  await expect
    .poll(async () => (await (await page.request.get(`/v1/orgs/${org}/matches/${match.id}/graphics`)).json()).analysis, { timeout: 240_000, intervals: [2000] })
    .toBe("ready");
  const video = (await (await page.request.get(`/v1/orgs/${org}/matches/${match.id}`)).json()).videos[0].id as string;

  // three goal candidates, apart, the strongest rate
  const rows = [8000, 16000, 24000]
    .map((ms, i) => `('${randomUUID()}', '${org}', '${match.id}', '${video}', 'goal', ${ms + 1500}, ${ms}, ${ms - 3000}, ${ms + 3000}, ${3 - i * 0.1}, 1, ${i}, 'open')`)
    .join(", ");
  execFileSync("psql", [DB, "-qc", `INSERT INTO goal_candidates (id, organization_id, match_id, video_asset_id, kind, t_ms, goal_ms, start_ms, end_ms, score, rate, rank, status) VALUES ${rows}`]);

  // the start counts the court, the throw-off and the three goals: one count
  await page.goto(`/app/${org}/teams/${team}/matches`);
  await expect(page.getByTestId("start-next-step")).toContainText("5 Fragen helfen");

  // Prüfen: the court as it is, the throw-off at the start, two goals for us, one for them
  await page.goto(`/app/${org}/matches/${match.id}/check`);
  await expect(page.getByText("Frage 1 von 5")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Passt" }).click();
  await expect(page.getByText("Frage 2 von 5")).toBeVisible();
  await page.getByRole("button", { name: "Jetzt ist Anwurf" }).click();
  // each answer is saved before the next question shows
  for (const [n, who] of (["Tor HC Echt", "Tor TV Kandidat", "Tor HC Echt"] as const).entries()) {
    if (n < 2) await expect(page.getByText(`Frage ${n + 3} von 5`)).toBeVisible();
    else await expect(page.getByText("Frage 5 von 5")).toBeVisible();
    await page.getByRole("button", { name: who }).click();
  }
  await expect(page.getByRole("heading", { name: "Alles geprüft." })).toBeVisible();
  await expect(page.getByTestId("check-failed")).toHaveCount(0);

  // the start: the result of the video in the head, the course, the goals and their scene
  await page.goto(`/app/${org}/teams/${team}/matches`);
  await expect(page.getByTestId("score-note")).toHaveText("Tore im Video");
  await expect(page.locator("[data-zone=wurf]")).toContainText("2:1");
  // the course over the minutes the video covers
  await expect(page.locator("[data-zone=wurf] svg").filter({ visible: true }).first()).toBeVisible();
  const goals = page.getByTestId("video-goals");
  await expect(goals.getByTestId("video-goal")).toHaveCount(3);
  await expect(goals).toContainText("ohne Position");
  await expect(page.getByTestId("match-list")).toContainText("3 Tore im Video");
  // positions on the tactics camera: the court is confirmed and the scene has tracks
  await expect(goals.getByRole("img", { name: /Positionen aus dem Video/ })).toBeVisible({ timeout: 30_000 });
  await expect(goals.getByTestId("camera-empty")).toHaveCount(0);

  // the match: the same result and goals, the scenes in the Video tab
  await page.goto(`/app/${org}/matches/${match.id}`);
  await expect(page.locator("[data-zone=wurf]")).toContainText("2:1");
  await expect(page.getByTestId("video-goals").getByTestId("video-goal")).toHaveCount(3);
  await page.goto(`/app/${org}/matches/${match.id}?tab=video`);
  await expect(page.getByTestId("video-stage")).toBeVisible();
});

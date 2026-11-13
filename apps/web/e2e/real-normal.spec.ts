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
  // a newer match: the start's head shows it unless a fresh analysis waits
  await page.request.post(`/v1/orgs/${org}/teams/${team}/matches`, {
    headers: { "x-csrf-token": csrf },
    data: { opponent_name: "TV Neuer", kickoff_at: new Date(Date.now() - 7_200_000).toISOString() },
  });
  await page.goto(`/app/${org}/matches/${match.id}?tab=video`);
  await page.getByTestId("video-file").setInputFiles(MATCH_VIDEO);
  await expect(page.getByTestId("plain-stage")).toBeVisible({ timeout: 240_000 });
  // away from the match while the analysis runs: it is not opened after it
  await page.goto(`/app/${org}/teams/${team}/matches`);
  await expect
    .poll(async () => (await (await page.request.get(`/v1/orgs/${org}/matches/${match.id}/graphics`)).json()).analysis, { timeout: 240_000, intervals: [2000] })
    .toBe("ready");
  const video = (await (await page.request.get(`/v1/orgs/${org}/matches/${match.id}`)).json()).videos[0].id as string;

  // three goal candidates, apart, the strongest rate
  const rows = [8000, 16000, 24000]
    .map((ms, i) => `('${randomUUID()}', '${org}', '${match.id}', '${video}', 'goal', ${ms + 1500}, ${ms}, ${ms - 3000}, ${ms + 3000}, ${3 - i * 0.1}, 1, ${i}, 'open', '${i === 1 ? "opponent" : "own"}')`)
    .join(", ");
  // and one weaker moment (29.6 s, apart from the goal at 24 s): not among the most important questions, but it could be a goal
  const weak = `('${randomUUID()}', '${org}', '${match.id}', '${video}', 'goal', 29800, 29600, 26000, 30000, 1.0, 3, 3, 'open')`;
  execFileSync("psql", [DB, "-qc", `INSERT INTO goal_candidates (id, organization_id, match_id, video_asset_id, kind, t_ms, goal_ms, start_ms, end_ms, score, rate, rank, status) VALUES ${weak}`]);
  execFileSync("psql", [DB, "-qc", `INSERT INTO goal_candidates (id, organization_id, match_id, video_asset_id, kind, t_ms, goal_ms, start_ms, end_ms, score, rate, rank, status, suggested_side) VALUES ${rows}`]);

  // the start counts the court, the throw-off and the three goals: one count
  await page.goto(`/app/${org}/teams/${team}/matches`);
  // the fresh analysis stands in the head, ahead of the newer match
  await expect(page.getByTestId("start-next-step")).toContainText("5 Fragen helfen");
  await expect(page.locator("[data-zone=wurf]")).toContainText("TV Kandidat");

  // the Spiel tab right after the analysis: the sentence and the step, not an empty tab (in a
  // second browser, so this browser has not opened the match yet)
  const second = await page.context().browser()!.newContext({ baseURL: info.project.use.baseURL, storageState: await page.context().storageState() });
  const tab = await second.newPage();
  await tab.goto(`/app/${org}/matches/${match.id}`);
  await expect(tab.getByTestId("game-step")).toHaveText("5 Fragen beantworten");
  await second.close();

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
  // one moment is still open: nothing looks final (third real-video test G1)
  await expect(page.getByTestId("check-main-done")).toContainText("Die wichtigsten Momente sind geprüft.");
  await expect(page.getByTestId("check-main-done")).toContainText("1 weiterer Moment könnte ein Tor sein.");
  await expect(page.getByRole("heading", { name: "Alles geprüft." })).toHaveCount(0);
  await expect(page.getByTestId("check-failed")).toHaveCount(0);
  // the head says interim, the count stays (in a second browser: this one has not opened the
  // match, so the start keeps it in its head below)
  const third = await page.context().browser()!.newContext({ baseURL: info.project.use.baseURL, storageState: await page.context().storageState() });
  const look = await third.newPage();
  await look.goto(`/app/${org}/matches/${match.id}`);
  await expect(look.getByTestId("score-note")).toHaveText("bisher bestätigt · 1 Moment offen");
  await expect(look.getByTestId("check-link")).toContainText("1");
  await third.close();
  await page.reload();
  await expect(page.getByTestId("check-main-done")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("check-more").click();
  // its clip holds the goal at 0:24 already confirmed: the question says so (real-video test G2)
  await expect(page.getByText("In diesem Ausschnitt liegt das Tor von 0:24, das du schon bestätigt hast.")).toBeVisible();
  await page.getByRole("button", { name: "Nein, dasselbe Tor" }).click();
  await expect(page.getByRole("heading", { name: "Alles geprüft." })).toBeVisible({ timeout: 30_000 });

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

  // the match: the same result and goals; «Szene zeigen» opens that scene in the Video tab
  await page.goto(`/app/${org}/matches/${match.id}`);
  await expect(page.locator("[data-zone=wurf]")).toContainText("2:1");
  await expect(page.getByTestId("game-next-step")).toHaveCount(0);
  await expect(page.getByTestId("video-goals").getByTestId("video-goal")).toHaveCount(3);
  await page.getByTestId("video-goals").getByTestId("scene-show").nth(1).click();
  await expect(page).toHaveURL(/tab=video.*scene=/);
  await expect(page.getByTestId("video-stage")).toBeVisible();
  // a short video: all its goals in the list, the second one running; the Rail over its minutes
  const scenes = page.getByTestId("stage-scenes").getByRole("button");
  await expect(scenes).toHaveCount(3);
  await expect(scenes.nth(1)).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("rail-span")).toBeVisible();
  await expect(page.getByTestId("rail-span")).not.toContainText("60");

  // opened and answered: the head goes back to the newer match
  await page.goto(`/app/${org}/teams/${team}/matches`);
  await expect(page.locator("[data-zone=wurf]")).toContainText("TV Neuer");
  await expect(page.locator("[data-zone=wurf]")).not.toContainText("TV Kandidat");
});

/**
 * Real-video test F3: a moved corner runs the analysis again. Prüfen waits visibly, then asks what
 * the server has open; it never says «Alles geprüft» while the server still has questions.
 */
test("a moved corner: Prüfen waits for the new analysis and asks what is open", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(300_000);
  await register(page, uniqueEmail("ecke"), "Coach Ecke");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Ecke");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, org, team] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const match = await (
    await page.request.post(`/v1/orgs/${org}/teams/${team}/matches`, {
      headers: { "x-csrf-token": csrf },
      data: { opponent_name: "TV Ecke", kickoff_at: new Date(Date.now() - 86_400_000).toISOString(), kit_opponent: "#f2f2f2" },
    })
  ).json();
  await page.goto(`/app/${org}/matches/${match.id}?tab=video`);
  await page.getByTestId("video-file").setInputFiles(MATCH_VIDEO);
  const analysis = async () => (await (await page.request.get(`/v1/orgs/${org}/matches/${match.id}/graphics`)).json()).analysis;
  await expect.poll(analysis, { timeout: 240_000, intervals: [2000] }).toBe("ready");

  await page.goto(`/app/${org}/matches/${match.id}/check`);
  await expect(page.getByText(/Frage 1 von \d+/)).toBeVisible({ timeout: 30_000 });
  // drag the near left corner a little and take the court
  const corner = page.getByTestId("corner-0");
  const box = (await corner.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 30, box.y + box.height / 2 - 10, { steps: 5 });
  await page.mouse.up();
  await page.getByRole("button", { name: "Passt" }).click();
  // the analysis runs again: Prüfen says so and waits, never «Alles geprüft» meanwhile
  await expect(page.getByTestId("check-reloading")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Alles geprüft." })).toHaveCount(0);
  // afterwards the server's open question (the throw-off) is asked
  await expect(page.getByRole("button", { name: "Jetzt ist Anwurf" })).toBeVisible({ timeout: 240_000 });
  await expect(page.getByTestId("check-failed")).toHaveCount(0);
  await page.getByRole("button", { name: "Jetzt ist Anwurf" }).click();
  await expect(page.getByRole("heading", { name: "Alles geprüft." })).toBeVisible({ timeout: 30_000 });
  expect(await analysis()).toBe("ready");
});

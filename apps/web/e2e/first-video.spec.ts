import { expect, test } from "@playwright/test";
import { MATCH_VIDEO } from "./global-setup";
import { expectAccessible, register, uniqueEmail } from "./helpers";

/**
 * UX test A02: after a first video in which the analysis finds no goals, the start says one
 * sentence and offers one next step; the match list says the state in words.
 */
test("start after a first video without goals: one sentence, one step", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(300_000);
  await register(page, uniqueEmail("a02"), "Coach Erstvideo");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Erstvideo");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, org, team] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const res = await page.request.post(`/v1/orgs/${org}/teams/${team}/matches`, {
    headers: { "x-csrf-token": csrf },
    data: { opponent_name: "TV Leerlauf", kickoff_at: new Date(Date.now() - 86_400_000).toISOString(), score_own: 25, score_opponent: 22 },
  });
  expect(res.ok()).toBeTruthy();
  const match = (await res.json()) as { id: string };

  await page.goto(`/app/${org}/matches/${match.id}?tab=video`);
  await page.getByTestId("video-file").setInputFiles(MATCH_VIDEO);
  await expect(page.getByTestId("plain-stage")).toBeVisible({ timeout: 240_000 });

  await page.goto(`/app/${org}/teams/${team}/matches`);
  const step = page.getByTestId("start-next-step");
  await expect(step).toBeVisible();
  // one sentence with the count of the questions, one button
  await expect(step.locator("p")).toHaveCount(1);
  await expect(step.locator("p")).toHaveText(/^Die Analyse hat noch keine Tore gefunden\. (1 Frage hilft|\d+ Fragen helfen) ihr weiter\.$/);
  await expect(step.getByTestId("start-step")).toHaveText("Fragen beantworten");
  // nothing that says the same again, no collection without scenes
  await expect(page.getByTestId("collection-from-match")).toHaveCount(0);
  await expect(page.getByText(/Für drei Dinge braucht es/)).toHaveCount(0);
  await expect(page.getByText(/danach Fragen zu den Personen/)).toHaveCount(0);
  // the list: the state in words
  await expect(page.getByTestId("match-list")).toContainText(/Analyse fertig, (1 Frage|\d+ Fragen) offen/);
  await expect(page.getByTestId("match-list")).not.toContainText("Kein Ding");
  // the start and Prüfen count the same questions
  const n = Number((await step.locator("p").textContent())!.match(/(\d+) Frage/)![1]);
  const g = await (await page.request.get(`/v1/orgs/${org}/matches/${match.id}/graphics`)).json();
  expect(g.checks.length).toBe(n);
  await expectAccessible(page);
});

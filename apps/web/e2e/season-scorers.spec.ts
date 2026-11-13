import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";
import * as fx from "./fixtures/entry";
import { register, uniqueEmail } from "./helpers";

const DB = process.env.E2E_DATABASE_URL ?? "postgresql://handball:handball@localhost:5432/handball";

/**
 * Third real-video test G6: «Wer trifft» of the season and the start counted the same twelve
 * match reports differently (6, 5, 4 against 50, 44, 36). With the team linked to handball.ch
 * both show the same count from the federation's player statistics; the answer of handball.ch
 * is recorded (fixtures/entry.ts), the test stack does not reach it.
 */
test("season and start: one count of the scorers", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(120_000);
  const h = fx.hit(81001, "SG Seeufer/Rebhalde");
  await page.route(/\/v1\/public\/clubs\/\d+\/teams\/\d+/, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fx.preview(h, true)) }),
  );
  await register(page, uniqueEmail("g6"), "Coach Zaehlung");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("SG Seeufer");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, org, team] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  // the team as linked to handball.ch (what taking it over from the official data stores)
  // a fresh official id per run: the link is unique per provider and team
  const officialId = 900_000 + Math.floor(Math.random() * 99_000);
  execFileSync("psql", [DB, "-qc", `UPDATE teams SET official_provider = 'handball_ch', official_team_id = ${officialId}, official_club_id = ${h.club.id} WHERE id = '${team}'`]);
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const m = await (
    await page.request.post(`/v1/orgs/${org}/teams/${team}/matches`, {
      headers: { "x-csrf-token": csrf },
      data: { opponent_name: "HC Uferweg", kickoff_at: new Date(Date.now() - 3 * 86_400_000).toISOString() },
    })
  ).json();
  const r = await page.request.patch(`/v1/orgs/${org}/matches/${m.id}`, { headers: { "x-csrf-token": csrf }, data: { score_own: 28, score_opponent: 26 } });
  expect(r.ok()).toBeTruthy();

  // the start: the scorers from the match reports
  await page.goto(`/app/${org}/teams/${team}/matches`);
  const start = page.getByTestId("start-from-report");
  await expect(start).toContainText("Lio Muster");
  await expect(start).toContainText("41");

  // the season: the same count, said from where
  await page.goto(`/app/${org}/teams/${team}/season`);
  const season = page.getByTestId("season-scorers-official");
  await expect(season).toContainText("aus 8 Spielberichten");
  await expect(season.getByRole("listitem").first()).toHaveText(/Lio Muster\s*41/);
  await expect(season.getByRole("listitem").nth(1)).toHaveText(/Nils Beispiel\s*33/);
});

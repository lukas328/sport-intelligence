import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";
import * as fx from "./fixtures/entry";
import { register, uniqueEmail } from "./helpers";

const DB = process.env.E2E_DATABASE_URL ?? "postgresql://handball:handball@localhost:5432/handball";

/**
 * One count of the scorers (third real-video test G6, app review R3): the start showed the
 * federation's statistics (41), the season, the roster and the player page the app's own (1).
 * Now every place counts the goals of the match reports in the app: the start shows the table
 * and the form from handball.ch but no scorers, the season counts the goals in the app, and a
 * goal a report gave by shirt number counts for the player once the number is in the roster.
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
  const headers = { "x-csrf-token": csrf };
  const m = await (
    await page.request.post(`/v1/orgs/${org}/teams/${team}/matches`, {
      headers,
      data: { opponent_name: "HC Uferweg", kickoff_at: new Date(Date.now() - 3 * 86_400_000).toISOString() },
    })
  ).json();
  const r = await page.request.patch(`/v1/orgs/${org}/matches/${m.id}`, { headers, data: { score_own: 28, score_opponent: 26 } });
  expect(r.ok()).toBeTruthy();
  // a goal of #9 as a report gives it, before #9 is in the roster
  const goal = await page.request.post(`/v1/orgs/${org}/matches/${m.id}/events`, { headers, data: { type: "shot", side: "own", outcome: "goal", clock_s: 300, number: 9 } });
  expect(goal.ok()).toBeTruthy();
  const info2 = await (await page.request.get(`/v1/orgs/${org}/teams/${team}`)).json();
  const roster = await page.request.post(`/v1/orgs/${org}/teams/${team}/seasons/${info2.current_season.id}/roster`, {
    headers,
    data: { first_name: "Lio", last_name: "Muster", jersey_number: 9 },
  });
  expect(roster.ok()).toBeTruthy();

  // the start: table and form from handball.ch, no second count of the scorers
  await page.goto(`/app/${org}/teams/${team}/matches`);
  const start = page.getByTestId("start-from-report");
  await expect(start).toBeVisible();
  await expect(start).not.toContainText("Lio Muster");

  // the season: the goal of the report, counted for the player
  await page.goto(`/app/${org}/teams/${team}/season`);
  const season = page.getByTestId("season-scorers");
  await expect(season).toContainText("aus 1 Spiel");
  await expect(season.getByRole("row").nth(1)).toContainText("Lio Muster");
  await expect(season.getByRole("row").nth(1)).toContainText("1");
});

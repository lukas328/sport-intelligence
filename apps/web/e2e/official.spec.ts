import { expect, test, type Page, type Route } from "@playwright/test";
import * as fx from "./fixtures/official";
import { expectAccessible, register, uniqueEmail } from "./helpers";

// The official data come from handball.ch, which the test stack does not reach: the API's answers
// are recorded with invented names (fixtures/official.ts) and given to the browser. What runs for
// real: the pages, their state and the requests they send.

const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

test("onboarding: find the team, take one over, ask a claimed club for access, ask to join as a player", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  const claims: { id: string; body: unknown }[] = [];
  let joined: unknown = null;
  await page.route("**/v1/official/teams?*", (route) => {
    const q = new URL(route.request().url()).searchParams.get("q") ?? "";
    return json(route, /seeblick|bergtal|see/i.test(q) ? fx.searchHits : []);
  });
  await page.route("**/v1/official/teams/*/claim", (route) => {
    const id = route.request().url().split("/").at(-2)!;
    claims.push({ id, body: route.request().postDataJSON() });
    return id === "72001" ? json(route, fx.accessRequested, 202) : json(route, fx.claimed(fx.CLAIMED_ORG, fx.CLAIMED_TEAM), 201);
  });
  await page.route(`**/v1/teams/${fx.CLAIMED_TEAM}/join-requests`, (route) => {
    joined = route.request().postDataJSON();
    return json(route, fx.joinRequested, 201);
  });

  await register(page, uniqueEmail("official"), "Coach Offiziell");
  await expect(page).toHaveURL(/\/onboarding/);
  const search = page.getByTestId("official-search");
  await search.getByLabel("Team oder Verein").fill("Seeblick");
  const results = page.getByRole("list", { name: "Gefundene Teams" });
  // grouped by club; a team already in the app shows who decides
  await expect(results.getByRole("heading", { name: /HC Seeblick/ })).toBeVisible();
  await expect(results.getByRole("heading", { name: /SG Bergtal/ })).toBeVisible();
  await expect(page.getByTestId("official-team")).toHaveCount(3);
  await expect(page.getByTestId("official-team").filter({ hasText: "SG Bergtal Herren" })).toContainText("schon in der App");
  await expectAccessible(page);

  // a coach of the claimed club asks its admins for access, with a message
  const bergtal = page.getByTestId("official-team").filter({ hasText: "SG Bergtal Herren" });
  await bergtal.getByRole("button", { name: "Zugang anfragen" }).click();
  await bergtal.getByLabel(/Nachricht/).fill("Ich trainiere die Herren seit diesem Sommer.");
  await bergtal.getByRole("button", { name: "Anfrage senden" }).click();
  await expect(page.getByText("Anfrage gesendet. Die Admins von SG Bergtal melden sich in der App.")).toBeVisible();
  expect(claims.at(-1)).toEqual({ id: "72001", body: { club_id: 9002, message: "Ich trainiere die Herren seit diesem Sommer." } });

  // a player asks to join that team
  await bergtal.getByRole("button", { name: "Als Spieler/in beitreten" }).click();
  await bergtal.getByLabel("Vorname").fill("Lara");
  await bergtal.getByLabel("Nachname").fill("Muster");
  await bergtal.getByLabel(/Rückennummer/).fill("11");
  await bergtal.getByRole("button", { name: "Beitritt anfragen" }).click();
  await expect(page.getByText("Anfrage gesendet. Sobald sie bestätigt ist, bist du im Team SG Bergtal Herren.")).toBeVisible();
  expect(joined).toMatchObject({ first_name: "Lara", last_name: "Muster", jersey_number: 11, role: "player" });
  // the coach's steps (club, team, squad, invite) are not the player's
  await expect(page.getByText(/Schritt 1 von/)).toHaveCount(0);

  // an available team is taken over: step 2 «Ist das dein Team?» shows what came with it
  const claimedBase = `**/v1/orgs/${fx.CLAIMED_ORG}/teams/${fx.CLAIMED_TEAM}`;
  const accepted: string[] = [];
  let patched: unknown = null;
  await page.route(`${claimedBase}/official`, (route) => json(route, fx.link));
  await page.route(`${claimedBase}/official/suggestions*`, (route) => json(route, fx.suggestions));
  await page.route(`${claimedBase}/official/suggestions/*/accept`, (route) => {
    accepted.push(route.request().url().split("/").at(-2)!);
    return json(route, {});
  });
  await page.route(`${claimedBase}/matches`, (route) =>
    json(route, [
      { id: "00000000-0000-4000-8000-00000000a001", team_id: fx.CLAIMED_TEAM, kind: "match", kickoff_at: "2026-11-07T17:00:00Z", opponent_name: "TSV Thalwil", is_home: true, score_own: 26, score_opponent: 18, status: "finished", has_video: false, is_demo: false, competition: null },
      { id: "00000000-0000-4000-8000-00000000a002", team_id: fx.CLAIMED_TEAM, kind: "match", kickoff_at: "2026-11-22T18:30:00Z", opponent_name: "HSG Rheinau", is_home: false, score_own: null, score_opponent: null, status: "scheduled", has_video: false, is_demo: false, competition: null },
    ]),
  );
  await page.route(`**/v1/orgs/${fx.CLAIMED_ORG}`, (route) => {
    if (route.request().method() !== "PATCH") return route.fallback();
    patched = route.request().postDataJSON();
    return json(route, {});
  });
  await page.getByTestId("official-team").filter({ hasText: "HC Seeblick Herren 1" }).getByTestId("claim").click();
  await expect(page.getByRole("heading", { level: 1, name: "Ist das dein Team?" })).toBeVisible();
  await expect(page.getByText("Schritt 2 von 2")).toBeVisible();
  const done = page.getByTestId("claim-done");
  await expect(done.getByRole("heading", { name: "HC Seeblick Herren 1" })).toBeVisible();
  await expect(done).toContainText("3 Personen im Kader, mit Nummern");
  await expect(done).toContainText("2 Spiele im Spielplan, 1 gespielt");
  await expect(done).toContainText("Tabelle: Rang 2");
  // the preview: the last match's head and two squad rows
  await expect(done).toContainText("Gewonnen.");
  await expect(done).toContainText("Timo Brunner");
  expect(claims.at(-1)).toEqual({ id: "71001", body: { club_id: 9001 } });
  // the shirt is the label of its radio: a click on it picks the colour
  await done.locator("label", { has: page.getByRole("radio", { name: "Rot" }) }).click();
  await expect(done.getByRole("radio", { name: "Rot" })).toBeChecked();
  await expectAccessible(page);
  await done.getByRole("button", { name: "Stimmt, weiter" }).filter({ visible: true }).click();
  await page.waitForURL(new RegExp(`/app/${fx.CLAIMED_ORG}/teams/${fx.CLAIMED_TEAM}/matches$`));
  expect(patched).toEqual({ primary_color: "#d3202e" });
  // the players who played come into the squad; Nico Zemp (no game yet) waits in the inbox
  expect(accepted).toHaveLength(2);
});

/** A club and team made by hand, then the official answers for that team. */
async function coachWithTeam(page: Page) {
  await register(page, uniqueEmail("official-inbox"), "Coach Abgleich");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Seeblick");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/app\/[^/]+\/teams\/[^/?#]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  return { orgId: orgId!, teamId: teamId! };
}

test("suggestion inbox: squad with a doubled number, a report to import, the table", async ({ page }) => {
  const { orgId, teamId } = await coachWithTeam(page);
  const base = `**/v1/orgs/${orgId}/teams/${teamId}/official`;
  let open = [...fx.suggestions];
  const accepted: { id: string; body: unknown }[] = [];
  await page.route(base, (route) => json(route, fx.link));
  await page.route(`${base}/suggestions?*`, (route) => json(route, open));
  await page.route(`${base}/suggestions/*/accept`, (route) => {
    const id = route.request().url().split("/").at(-2)!;
    accepted.push({ id, body: route.request().postDataJSON() });
    const s = open.find((x) => x.id === id)!;
    open = open.filter((x) => x.id !== id);
    return json(route, { suggestion: { ...s, status: "accepted", resolved_at: new Date().toISOString() }, player_id: null, match_id: null, season_id: null });
  });

  await page.goto(`/app/${orgId}/teams/${teamId}/official`);
  await expect(page.getByRole("heading", { level: 1, name: "Abgleich mit handball.ch" })).toBeVisible();
  await expect(page.getByText("Herren 3. Liga · Gruppe 2")).toBeVisible();

  // the squad: players with games are ticked, the one without is not; #7 is there twice
  const squad = page.getByTestId("official-squad");
  await expect(squad.getByTestId("roster-suggestion")).toHaveCount(3);
  await expect(squad.getByRole("checkbox", { name: "Timo Brunner übernehmen" })).toBeChecked();
  await expect(squad.getByRole("checkbox", { name: "Nico Zemp übernehmen" })).not.toBeChecked();
  await expect(squad.getByText("Doppelte Rückennummer: 7.", { exact: false })).toBeVisible();
  await expect(page.getByTestId("take-squad")).toBeDisabled();
  await expectAccessible(page);

  await squad.getByLabel("Rückennummer von Jonas Amrein").fill("17");
  await expect(page.getByTestId("take-squad")).toHaveText("2 Spieler/innen übernehmen");
  await page.getByTestId("take-squad").click();
  await expect(page.getByText("2 Spieler/innen im Team.")).toBeVisible();
  expect(accepted.map((a) => a.body)).toEqual([{ jersey_number: 7 }, { jersey_number: 17 }]);
  await expect(squad.getByTestId("roster-suggestion")).toHaveCount(1);

  // a report of a played game, imported with one click
  const reports = page.getByTestId("official-reports");
  await expect(reports).toContainText("TV Talwiese");
  await expect(reports).toContainText("27:25");
  await reports.getByRole("button", { name: "Importieren" }).click();
  await expect(page.getByText("Übernommen.")).toBeVisible();
  await expect(page.getByTestId("official-reports")).toHaveCount(0);

  // the table marks the own team
  await expect(page.getByTestId("official-standing").locator("tr[aria-current]")).toContainText("HC Seeblick Herren 1");
  await expectAccessible(page);
});

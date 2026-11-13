import { expect, test } from "@playwright/test";
import { expectAccessible, follow, linkFromMail, register, uniqueEmail, openTraining } from "./helpers";

// The player's side of a match: the way to their own scenes, before and after the
// self-assessment. Scenes come from the analysis; the list of the player's feeds is answered
// here (an analysed match with a feed needs real footage).
test("player: the match page leads to the own scenes, assessment first", async ({ page, browser }, info) => {
  test.skip(info.project.name !== "chromium", "full flow runs once");
  await register(page, uniqueEmail("coach-player"), "Coach Szenen");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Szenen");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Damen 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  // invitations live in the club now, not in the onboarding (UX test B27)
  const teamUrl0 = page.url();
  await page.goto(`/app/${orgId}/club/teams`);
  const playerEmail = uniqueEmail("player-scenes");
  await page.getByLabel("E-Mail").fill(playerEmail);
  await page.getByRole("button", { name: "Einladung senden" }).click();
  await expect(page.getByText(`Eingeladen: ${playerEmail}`)).toBeVisible();
  await page.goto(teamUrl0);
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Testdorf");
  await page.getByRole("button", { name: "Spiel anlegen" }).click();
  await page.waitForURL(/\/matches\/[0-9a-f-]{36}/);
  const matchId = page.url().match(/\/matches\/([0-9a-f-]{36})/)![1]!;

  // the coach sees who replied to the match and notes who came
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const team = await (await page.request.get(`/v1/orgs/${orgId}/teams/${teamId}`)).json();
  await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/seasons/${team.current_season.id}/roster`, {
    headers: { "x-csrf-token": csrf },
    data: { first_name: "Lea", last_name: "Beispiel", jersey_number: 9 },
  });
  // replies, the player area and the parent area are «Teamfunktionen», off for a new team (ADR 029)
  await page.request.patch(`/v1/orgs/${orgId}/teams/${teamId}`, { headers: { "x-csrf-token": csrf }, data: { settings: { team_features: true } } });
  await page.reload();
  const attendance = page.getByTestId("match-attendance");
  await attendance.locator("summary").click();
  await expect(attendance).toContainText("0 Zusagen, 0 Absagen, 1 offen");
  await attendance.getByLabel("Anwesenheit von Lea Beispiel").selectOption("present");
  await page.reload();
  await page.getByTestId("match-attendance").locator("summary").click();
  await expect(page.getByTestId("match-attendance").getByLabel("Anwesenheit von Lea Beispiel")).toHaveValue("present");
  await expectAccessible(page);

  // the squad: Lea is injured until next week, then fit again
  await page.goto(`/app/${orgId}/teams/${teamId}?edit=1`);
  const lea = page.getByTestId("roster-row").filter({ hasText: "Lea" });
  await lea.getByRole("button", { name: "Status: Lea Beispiel" }).click();
  const form = page.getByRole("form", { name: "Status von Lea Beispiel" });
  await form.getByLabel("Status").selectOption("injured");
  const until = new Date(Date.now() + 7 * 86400_000);
  await form.getByLabel(/Bis und mit/).fill(until.toISOString().slice(0, 10));
  await form.getByLabel(/Notiz/).fill("Knöchel");
  await form.getByRole("button", { name: "Speichern" }).click();
  await expect(lea.getByTestId("player-status")).toContainText("Verletzt bis");
  await expect(lea.getByTestId("player-status")).toContainText("Knöchel");
  await expect(page.getByTestId("roster-availability")).toHaveText("Verfügbar 0 von 1 · Lea Beispiel fällt aus");
  await expectAccessible(page);

  // a unit in two days: the plan says who is out that day
  await openTraining(page);
  await page.getByRole("button", { name: "Neue Einheit" }).click();
  const unit = page.getByRole("form", { name: "Neue Einheit" });
  await unit.getByLabel("Datum").fill(new Date(Date.now() + 2 * 86400_000).toISOString().slice(0, 10));
  await unit.getByLabel("Titel").fill("Abwehr 6:0");
  await unit.getByRole("button", { name: "Speichern" }).click();
  await expect(page.getByTestId("session-out")).toHaveText("1 fällt aus: Lea Beispiel (verletzt)");
  await page.goto(`/app/${orgId}/teams/${teamId}?edit=1`);
  await lea.getByRole("button", { name: "Status: Lea Beispiel" }).click();
  await page.getByRole("form", { name: "Status von Lea Beispiel" }).getByLabel("Status").selectOption("fit");
  await page.getByRole("form", { name: "Status von Lea Beispiel" }).getByRole("button", { name: "Speichern" }).click();
  await expect(lea.getByTestId("player-status")).toHaveCount(0);

  const link = await linkFromMail(page, playerEmail, "/invite/");
  const ctx = await browser.newContext();
  const player = await ctx.newPage();
  await player.goto(link);
  await player.getByRole("link", { name: "Konto erstellen und annehmen" }).click();
  await player.getByLabel("Vor- und Nachname").fill("Mia Muster");
  await player.getByLabel("Passwort").fill("correct-horse-1");
  await player.getByLabel(/Nutzungsbedingungen/).check();
  await player.getByRole("button", { name: "Konto erstellen" }).click();
  await player.waitForURL((url) => !url.pathname.startsWith("/register"), { timeout: 30_000 });

  const playerId = "00000000-0000-4000-8000-000000000a01";
  let assessed = false;
  await player.route(`**/v1/orgs/${orgId}/me/feeds`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([{ player_id: playerId, player_first_name: "Mia", relation: "self", match_id: matchId, kickoff_at: new Date().toISOString(), opponent: "TV Testdorf", assessed }]),
    }),
  );
  await player.goto(`/app/${orgId}/matches/${matchId}`);
  const mine = player.getByTestId("my-scenes");
  await expect(mine).toContainText("Deine Szenen");
  await expect(mine).toContainText("Zuerst deine Einschätzung");
  await expect(mine.getByRole("link", { name: "Jetzt einschätzen" })).toHaveAttribute("href", `/app/${orgId}/feed/${matchId}?player=${playerId}`);
  await expectAccessible(player);

  // after the self-assessment the same line leads to the scenes and the coach's notes
  assessed = true;
  await player.reload();
  await expect(mine.getByRole("link", { name: "Szenen ansehen" })).toBeVisible();

  // the overview: the next date is answered on the stage, the later ones without a reply are a to-do
  const day = (n: number) => new Date(Date.now() + n * 86400_000).toISOString().slice(0, 10);
  const date = (n: number, response: "yes" | "no" | null) => ({
    kind: "session", id: `00000000-0000-4000-8000-00000000b00${n}`, title: "Training", team: "Damen 1", on_date: day(n), starts_at: null,
    player_id: playerId, player_name: "Mia Muster", relation: "self", response,
  });
  await player.route(`**/v1/orgs/${orgId}/me/schedule`, (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify([date(1, null), date(3, null), date(5, "yes"), date(8, null)]) }),
  );
  await player.goto(`/app/${orgId}`);
  await expect(player.getByRole("link", { name: /2 Termine beantworten/ })).toHaveAttribute("href", `/app/${orgId}/schedule`);
  await expectAccessible(player);
  await ctx.close();

  // the coach gives the team a drill: who has done it, and who not yet, by name
  await page.goto(`/app/${orgId}/teams/${teamId}/assignments`);
  await page.getByLabel("Art").selectOption("drill");
  await page.getByRole("button", { name: "Teilen", exact: true }).click();
  const assignment = page.getByTestId("team-assignments").getByRole("listitem").first();
  await expect(assignment.getByTestId("assignment-progress")).toHaveText("0 von 1 erledigt");
  await expect(assignment.getByTestId("assignment-open")).toHaveText("Noch offen: Mia Muster");
  await expectAccessible(page);

  // the squad: Mia's account belongs to no entry yet; the coach links it, sees it, and unlinks it
  await page.goto(`/app/${orgId}/teams/${teamId}?edit=1`);
  const unlinked = page.getByTestId("unlinked-accounts");
  await expect(unlinked).toContainText("1 Konto ohne Eintrag im Team");
  const linkForm = unlinked.getByRole("form", { name: "Mia Muster verknüpfen" });
  await linkForm.getByLabel("Eintrag im Team").selectOption({ label: "#9 Lea Beispiel" });
  await linkForm.getByRole("button", { name: "Verknüpfen" }).click();
  await expect(unlinked).toHaveCount(0);
  await lea.getByRole("button", { name: "Status: Lea Beispiel" }).click();
  await expect(lea.getByTestId("account-line")).toContainText("Konto: Mia Muster");
  await lea.getByRole("button", { name: "Lösen" }).click();
  await expect(page.getByTestId("unlinked-accounts")).toContainText("Mia Muster");

  // consents per person and purpose, before filming
  await page.getByText("Einwilligungen pro Person und Zweck").click();
  const consents = page.getByTestId("consent-overview");
  await expect(consents.getByRole("columnheader", { name: /Videoanalyse im Team/ })).toContainText("0 von 1");
  await expect(consents.getByRole("row", { name: /Lea Beispiel/ })).toContainText("fehlt");
  await expectAccessible(page);

  // the invitation offers the free squad entry for a player
  await page.goto(`/app/${orgId}/club/teams`);
  const invite = page.getByRole("form", { name: "Person einladen" });
  await expect(invite.getByLabel("Im Team").locator("option", { hasText: "#9 Lea Beispiel" })).toHaveCount(1);

  // Lea's season line from her name in the squad: no played match yet
  await page.goto(`/app/${orgId}/teams/${teamId}`);
  await page.getByRole("link", { name: "Lea Beispiel" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "#9 Lea Beispiel" })).toBeVisible();
  await expect(page.getByTestId("season-line-empty")).toContainText("Noch kein gespieltes Spiel in dieser Saison.");
  await expectAccessible(page);
});

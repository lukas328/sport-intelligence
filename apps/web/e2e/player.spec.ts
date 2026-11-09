import { expect, test } from "@playwright/test";
import { expectAccessible, follow, linkFromMail, register, uniqueEmail } from "./helpers";

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
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  const playerEmail = uniqueEmail("player-scenes");
  await page.getByLabel("E-Mail").fill(playerEmail);
  await page.getByRole("button", { name: "Einladung senden" }).click();
  await expect(page.getByText(`Eingeladen: ${playerEmail}`)).toBeVisible();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId] = page.url().match(/\/app\/([^/]+)\/teams\//)!;
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Testdorf");
  await page.getByRole("button", { name: "Spiel anlegen" }).click();
  await page.waitForURL(/\/matches\/[0-9a-f-]{36}/);
  const matchId = page.url().match(/\/matches\/([0-9a-f-]{36})/)![1]!;

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
});

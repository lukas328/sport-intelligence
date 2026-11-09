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
  await ctx.close();
});

import { expect, test } from "@playwright/test";
import { expectAccessible, linkFromMail, register, uniqueEmail } from "./helpers";

// Addendum 01: parent role, consent per purpose, youth protection, similar-kit warning
test("parent consents for own child; coach sees kit warning", async ({ page, context, browser }, info) => {
  test.skip(info.project.name !== "chromium", "full flow runs once");
  await register(page, uniqueEmail("coach-family"), "Coach Junior");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Familie");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("U13");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;

  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  const team = await (await page.request.get(`/v1/orgs/${orgId}/teams/${teamId}`)).json();
  await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/seasons/${team.current_season.id}/roster`, {
    headers: { "x-csrf-token": csrf },
    data: { first_name: "Noah", last_name: "Kind", jersey_number: 5, birth_year: 2014 },
  });

  // coach invites a parent for Noah
  await page.goto(`/app/${orgId}/club/teams`);
  const parentEmail = uniqueEmail("parent");
  const invite = page.getByRole("form", { name: "Person einladen" });
  await invite.getByLabel("E-Mail").fill(parentEmail);
  await invite.getByLabel("Rolle").selectOption("parent");
  await expect(invite.getByLabel("Kind")).toContainText("Noah Kind");
  await invite.getByRole("button", { name: "Einladung senden" }).click();
  await expect(page.getByText(`Eingeladen: ${parentEmail}`)).toBeVisible();

  // the parent accepts and consents to video analysis for the child only
  const link = await linkFromMail(page, parentEmail, "/invite/");
  const ctx = await browser.newContext();
  const parent = await ctx.newPage();
  await parent.goto(link);
  await parent.getByRole("link", { name: "Konto erstellen und annehmen" }).click();
  await parent.getByLabel("Vor- und Nachname").fill("Eva Kind");
  await parent.getByLabel("Passwort").fill("correct-horse-1");
  await parent.getByLabel(/Nutzungsbedingungen/).check();
  await parent.getByRole("button", { name: "Konto erstellen" }).click();
  await parent.waitForURL((url) => !url.pathname.startsWith("/register"), { timeout: 30_000 });
  await parent.goto(`/app/${orgId}/consents`);
  const child = parent.getByRole("region", { name: /Noah Kind/ });
  await expect(child).toContainText("Dein Kind");
  await expectAccessible(parent);
  await child.getByRole("button", { name: "Einwilligen: Videoanalyse im Team" }).click();
  await expect(child.getByRole("button", { name: "Zurückziehen: Videoanalyse im Team" })).toBeVisible();
  // youth: nothing public
  await expect(child.getByRole("button", { name: /Öffentliches Profil/ })).toHaveCount(0);
  // parents do not see the team
  const res = await parent.request.get(`/v1/orgs/${orgId}/teams/${teamId}`);
  expect([403, 404]).toContain(res.status());
  await ctx.close();

  // coach: similar kits are flagged while creating a match
  await page.goto(`/app/${orgId}/teams/${teamId}/matches`);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Rot");
  await page.getByText("Mehr: Wettbewerb, Halle, Spieldauer, Trikots").click();
  await expect(page.getByLabel("Spieldauer")).toHaveValue("adult_2x30");
  await page.getByLabel("Gegner Feldspieler").fill("#0d6ccc");
  await expect(page.getByTestId("kit-warning")).toContainText("Eigenes Team / Gegner");
  await expectAccessible(page);
});

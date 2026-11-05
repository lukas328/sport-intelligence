import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { Secret, TOTP } from "otpauth";
import { expectAccessible, linkFromMail, register, uniqueEmail } from "./helpers";

const fixtures = path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures");

test.describe.configure({ mode: "serial" });

test("redirects to login without session", async ({ page }) => {
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login\?next=%2Fapp/);
  await expect(page.getByRole("heading", { name: "Anmelden" })).toBeVisible();
  await expectAccessible(page);
});

test("new club: club, team and roster in under 5 minutes, then invite a player", async ({ page, browser }, info) => {
  test.skip(info.project.name !== "chromium", "full flow runs once");
  const started = Date.now();
  const coachEmail = uniqueEmail("coach");

  await register(page, coachEmail, "Sandra Trainerin");
  await expect(page).toHaveURL(/\/onboarding/);
  await expectAccessible(page);

  // step 1: club
  await page.getByLabel("Vereinsname").fill("HC E2E Zürich");
  await page.getByLabel("Logo (optional)").setInputFiles(path.join(fixtures, "logo.png"));
  await page.getByRole("button", { name: "Weiter", exact: true }).click();

  // step 2: team
  await expect(page.getByLabel("Teamname")).toBeVisible();
  await expectAccessible(page);
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByLabel("Liga (optional)").fill("3. Liga");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();

  // step 3: roster by hand
  const form = page.getByRole("form", { name: "Spieler hinzufügen" });
  await expect(form).toBeVisible();
  await form.getByLabel("Nr.").fill("7");
  await form.getByLabel("Vorname").fill("Lena");
  await form.getByLabel("Nachname").fill("Meier");
  await form.getByLabel("Position").selectOption("RA");
  await form.getByRole("button", { name: "Hinzufügen" }).click();
  await expect(page.getByText("Lena Meier wurde hinzugefügt.")).toBeVisible();
  await form.getByLabel("Nr.").fill("7");
  await form.getByLabel("Vorname").fill("Mia");
  await form.getByLabel("Nachname").fill("Doppel");
  await form.getByRole("button", { name: "Hinzufügen" }).click();
  await expect(page.getByText("Diese Rückennummer ist in der Saison schon vergeben.")).toBeVisible();

  // step 3: roster by CSV
  await page.getByLabel("CSV-Datei").setInputFiles(path.join(fixtures, "kader.csv"));
  await page.getByRole("button", { name: "Prüfen" }).click();
  await expect(page.getByTestId("csv-preview")).toContainText("Noah Keller");
  await page.getByRole("button", { name: "3 Spieler importieren" }).click();
  await expect(page.getByText("3 Spieler importiert.")).toBeVisible();
  await expect(page.getByTestId("roster-row")).toHaveCount(4);
  await expectAccessible(page);
  await page.getByRole("button", { name: "Weiter", exact: true }).click();

  // step 4: invite a player
  const playerEmail = uniqueEmail("player");
  await page.getByLabel("E-Mail").fill(playerEmail);
  await page.getByRole("button", { name: "Einladung senden" }).click();
  await expect(page.getByText(`Eingeladen: ${playerEmail}`)).toBeVisible();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Kader" })).toBeVisible();
  await expect(page.getByText("Team · Herren 1")).toBeVisible();
  await expect(page.getByTestId("roster-count")).toHaveText("4 Spieler");

  const elapsed = Date.now() - started;
  expect(elapsed, "onboarding must take under 5 minutes").toBeLessThan(5 * 60 * 1000);
  console.log(`onboarding flow took ${(elapsed / 1000).toFixed(1)} s`);

  // the invited player accepts via the e-mail link in a separate browser
  const link = await linkFromMail(page, playerEmail, "/invite/");
  const ctx = await browser.newContext();
  const player = await ctx.newPage();
  await player.goto(link);
  await expect(player.getByText("Du bist eingeladen zu HC E2E Zürich.")).toBeVisible();
  await expectAccessible(player);
  await player.getByRole("link", { name: "Konto erstellen und annehmen" }).click();
  await expect(player.getByLabel("E-Mail")).toHaveValue(playerEmail);
  await player.getByLabel("Vor- und Nachname").fill("Paul Spieler");
  await player.getByLabel("Passwort").fill("correct-horse-1");
  await player.getByLabel(/Nutzungsbedingungen/).check();
  await player.getByRole("button", { name: "Konto erstellen" }).click();
  await expect(player.getByRole("main")).toContainText("Paul");
  // players see four places: today, clips, dates, team
  await expect(player.getByRole("navigation", { name: "Hauptnavigation" }).getByRole("link")).toHaveCount(4);
  await player.getByRole("link", { name: "Team", exact: true }).click();
  await expect(player.getByTestId("roster-row")).toHaveCount(4);
  // players cannot edit the roster
  await expect(player.getByRole("form", { name: "Spieler hinzufügen" })).toHaveCount(0);
  await ctx.close();

  // settings: pending invitations are empty now, members list shows the player
  await page.getByTestId("account-menu").filter({ visible: true }).click();
  await page.getByRole("menuitem", { name: "Einstellungen" }).click();
  await expect(page.getByText("Paul Spieler")).toBeVisible();
  await expectAccessible(page);

  // enable two-factor sign-in, sign out, sign in with code
  await page.getByRole("button", { name: "Einrichten" }).click();
  const secret = (await page.getByTestId("totp-secret").textContent())!.trim();
  const totp = new TOTP({ secret: Secret.fromBase32(secret) });
  await page.getByLabel("Code").fill(totp.generate());
  await page.getByRole("button", { name: "Aktivieren", exact: true }).click();
  await expect(page.getByTestId("totp-state")).toContainText("Aktiv.");
  const recovery = (await page.getByTestId("recovery-codes").getByRole("listitem").first().textContent())!.trim();
  expect(recovery).toMatch(/^[a-z2-9]{4}-[a-z2-9]{4}$/);
  await page.getByTestId("account-menu").filter({ visible: true }).click();
  await page.getByRole("menuitem", { name: "Abmelden" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel("E-Mail").fill(coachEmail);
  await page.getByLabel("Passwort").fill("correct-horse-1");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Zwei-Faktor-Code" })).toBeVisible();
  await page.getByLabel("Code").fill(totp.generate());
  await page.getByRole("button", { name: "Bestätigen" }).click();
  await expect(page.getByRole("main")).toContainText("Sandra");

  // lost phone: a recovery code works once
  await page.getByTestId("account-menu").filter({ visible: true }).click();
  await page.getByRole("menuitem", { name: "Abmelden" }).click();
  await page.getByLabel("E-Mail").fill(coachEmail);
  await page.getByLabel("Passwort").fill("correct-horse-1");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.getByLabel("Code").fill(recovery);
  await page.getByRole("button", { name: "Bestätigen" }).click();
  await expect(page.getByRole("main")).toContainText("Sandra");
});

test("magic link sign-in", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  const email = uniqueEmail("magic");
  await register(page, email);
  await expect(page).toHaveURL(/\/onboarding/);
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByRole("button", { name: "Ohne Passwort anmelden" }).click();
  await page.getByLabel("E-Mail").fill(email);
  await page.getByRole("button", { name: "Link senden" }).click();
  await expect(page.getByText(/Link unterwegs/)).toBeVisible();
  await page.goto(await linkFromMail(page, email, "/auth/magic"));
  await expect(page).toHaveURL(/\/onboarding/);
});

test("wrong password shows a clear message", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("E-Mail").fill("nobody@hc-e2e.ch");
  await page.getByLabel("Passwort").fill("wrong-password-1");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page.getByText("E-Mail oder Passwort ist falsch.")).toBeVisible();
});

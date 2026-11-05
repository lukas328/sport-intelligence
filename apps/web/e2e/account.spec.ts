import { expect, test } from "@playwright/test";
import { expectAccessible, linkFromMail, register, uniqueEmail } from "./helpers";

test("forgot password: reset via e-mail link, then devices list", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  const email = uniqueEmail("reset");
  await register(page, email);
  await expect(page).toHaveURL(/\/onboarding/);
  await page.context().clearCookies();

  await page.goto("/login");
  await page.getByRole("link", { name: "Passwort vergessen?" }).click();
  await expect(page.getByRole("heading", { name: "Passwort zurücksetzen" })).toBeVisible();
  await expectAccessible(page);
  await page.getByLabel("E-Mail").fill(email);
  await page.getByRole("button", { name: "Link senden" }).click();
  await expect(page.getByText(/60 Minuten gültig/)).toBeVisible();

  await page.goto(await linkFromMail(page, email, "/auth/reset"));
  await page.getByLabel("Neues Passwort").fill("my-new-password-2");
  await page.getByRole("button", { name: "Passwort speichern" }).click();
  await expect(page).toHaveURL(/\/onboarding/);

  // old password no longer works, the new one does
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("E-Mail").fill(email);
  await page.getByLabel("Passwort").fill("correct-horse-1");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page.getByText("E-Mail oder Passwort ist falsch.")).toBeVisible();
  await page.getByLabel("Passwort").fill("my-new-password-2");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await expect(page).toHaveURL(/\/onboarding/);
});

test("e-mail verification link", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  const email = uniqueEmail("verify");
  await register(page, email);
  await page.goto(await linkFromMail(page, email, "/auth/verify"));
  await expect(page.getByText("Danke, deine E-Mail-Adresse ist bestätigt.")).toBeVisible();
  await expectAccessible(page);
});

test("login shows provider errors from the callback", async ({ page }) => {
  await page.goto("/login?error=oauth-cancelled");
  await expect(page.getByText("Die Anmeldung wurde abgebrochen.")).toBeVisible();
});

test("sign-in lands in the first club, server-rendered without errors", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  const email = uniqueEmail("signin");
  await register(page, email);
  await page.getByLabel("Vereinsname").fill("HC Anmeldung");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/app\/[^/]+\/teams\//);
  const orgId = page.url().match(/\/app\/([^/?#]+)/)![1]!;
  await page.context().clearCookies();

  // the shell used to fail its server render after push + refresh to /app ("Switched to client rendering")
  const errors: string[] = [];
  page.on("console", (m) => {
    if (
      m.type() === "error" &&
      /NextIntlClientProvider|Switched to client rendering/.test(m.text())
    )
      errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  const documents: string[] = [];
  page.on("request", (r) => {
    if (r.resourceType() === "document") documents.push(new URL(r.url()).pathname);
  });
  await page.goto("/login");
  await page.getByLabel("E-Mail").fill(email);
  await page.getByLabel("Passwort").fill("correct-horse-1");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL(new RegExp(`/app/${orgId}$`), { timeout: 30_000 });
  await expect(page.getByRole("link", { name: "Team", exact: true })).toBeVisible();
  // /app is answered by the server (first club) with one document request, not a client redirect chain
  expect(documents.filter((d) => d === "/app")).toHaveLength(1);
  expect(errors).toEqual([]);
});

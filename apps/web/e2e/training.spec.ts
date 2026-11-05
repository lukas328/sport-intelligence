import { expect, test } from "@playwright/test";
import { expectAccessible, register, uniqueEmail } from "./helpers";

test("drills, notifications and team assignments", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("train"), "Coach Training");
  await page.getByLabel("Vereinsname").fill("HC Training");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("U17");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  // the title names the page, the team sits in the eyebrow above it
  await expect(page.getByRole("heading", { level: 1, name: "Kader" })).toBeVisible();
  await expect(page.getByText("Team · U17")).toBeVisible();
  const teamUrl = page.url();

  // the bell shows no unread notifications for a new coach
  await expect(page.getByTestId("bell").filter({ visible: true })).toBeVisible();
  await page.getByTestId("bell").filter({ visible: true }).click();
  await expect(page.getByText("Keine Mitteilungen.")).toBeVisible();
  await page.keyboard.press("Escape");

  // drill library with focus filter
  await page.getByRole("link", { name: "Training", exact: true }).click();
  await page.getByRole("link", { name: "Übungen", exact: true }).click();
  await expect(page.getByTestId("drills").getByRole("listitem")).toHaveCount(11);
  await page.getByRole("link", { name: "Torhüter", exact: true }).click();
  await expect(page.getByTestId("drills").getByRole("listitem")).toHaveCount(2);
  await expectAccessible(page);

  // my assignments: empty
  await page.goto(teamUrl.replace(/\/teams\/.*/, "/assignments"));
  await expect(page.getByText("Keine Aufgaben.")).toBeVisible();

  // team assignments: a drill for everybody; without players the API explains why it cannot
  await page.goto(`${teamUrl}/assignments`);
  await page.getByLabel("Art").selectOption("drill");
  await page.getByRole("button", { name: "Aufgabe geben" }).click();
  await expect(page.getByText(/Lade zuerst Spieler/)).toBeVisible();
  await expectAccessible(page);

  // plan and usage in the settings (limits are not enforced in this installation)
  await page.goto(teamUrl.replace(/\/teams\/.*/, "/settings"));
  const billing = page.getByTestId("billing");
  await expect(billing).toContainText("Gratis");
  await expect(billing).toContainText("Limiten sind in dieser Installation nicht aktiv.");
  await expect(page.getByTestId("plans").getByRole("listitem").filter({ hasText: "CHF 39 pro Monat" })).toBeVisible();
  await expectAccessible(page);

  // privacy: personal data download and club deletion with name confirmation
  const exported = await page.request.get((await page.getByTestId("export").getAttribute("href"))!);
  expect((await exported.json()).account.name).toBe("Coach Training");
  await page.getByText("Verein löschen", { exact: true }).first().click();
  const del = page.getByRole("form", { name: "Verein löschen" });
  await del.getByLabel("Vereinsname").fill("HC Training");
  await del.getByRole("button", { name: "Verein löschen" }).click();
  await page.getByTestId("confirm-ok").click();
  await expect(page).toHaveURL(/\/onboarding/);
});

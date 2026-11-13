import { expect, test } from "@playwright/test";
import { expectAccessible, register, uniqueEmail, openTraining } from "./helpers";

test("drills, notifications and team assignments", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("train"), "Coach Training");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Training");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("U17");
  await page.getByRole("button", { name: "Zum Team" }).click();
  // the squad page says the state of the squad, the team sits in the eyebrow above it
  await expect(page.getByRole("heading", { level: 1, name: "Noch niemand im Kader." })).toBeVisible();
  await expect(page.getByText(/^U17 · /)).toBeVisible();
  const teamUrl = page.url();

  // the bell shows no unread notifications for a new coach
  await expect(page.getByTestId("bell").filter({ visible: true })).toBeVisible();
  await page.getByTestId("bell").filter({ visible: true }).click();
  await expect(page.getByText("Keine Mitteilungen.")).toBeVisible();
  await page.keyboard.press("Escape");

  // drill library with focus filter
  await openTraining(page);
  await page.getByRole("link", { name: "Übungen", exact: true }).click();
  await expect(page.getByTestId("drills").getByRole("listitem")).toHaveCount(11);
  await page.getByRole("link", { name: "Torhüter", exact: true }).click();
  await expect(page.getByTestId("drills").getByRole("listitem")).toHaveCount(2);

  // an own drill, shared in the club: it sits above the library and in the unit's drill list
  await page.getByRole("link", { name: "Alle", exact: true }).click();
  await page.getByTestId("drill-new").click();
  const drill = page.getByRole("form", { name: "Neue Übung" });
  await drill.getByLabel("Name").fill("Kreuzen im Rückraum");
  await drill.getByLabel("Minuten").fill("20");
  await drill.getByLabel("Rückraum").check();
  await drill.getByLabel("Aufbau").fill("Zwei Rückraumspieler kreuzen, Kreis sperrt.");
  await drill.getByLabel(/Im Verein teilen/).check();
  await drill.getByRole("button", { name: "Speichern" }).click();
  const own = page.getByTestId("club-drill").filter({ hasText: "Kreuzen im Rückraum" });
  await expect(own).toContainText("Eigene Übung, im Verein geteilt");
  await expect(own).toContainText("Rückraum · 20 min");
  await expectAccessible(page);
  await expectAccessible(page);

  // tasks are team functions (SPEC 6): without them the pages lead back to Spiele, so switch them on
  const [, orgId, teamId] = teamUrl.match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  await page.goto(`/app/${orgId}/assignments`);
  await page.waitForURL(/\/matches/);
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  await page.request.patch(`/v1/orgs/${orgId}/teams/${teamId}`, { headers: { "x-csrf-token": csrf }, data: { settings: { team_features: true } } });

  // my assignments: empty
  await page.goto(teamUrl.replace(/\/teams\/.*/, "/assignments"));
  await expect(page.getByText("Keine offenen Aufgaben.")).toBeVisible();

  // team assignments: a drill for everybody; without players the API explains why it cannot
  await page.goto(`${teamUrl}/assignments`);
  await page.getByLabel("Art").selectOption("drill");
  await page.getByRole("button", { name: "Teilen", exact: true }).click();
  await expect(page.getByText(/Lade zuerst Spieler/)).toBeVisible();
  await expectAccessible(page);

  // plan and usage under Verein, Abo und Rechnungen (limits are not enforced in this installation)
  await page.goto(teamUrl.replace(/\/teams\/.*/, "/club/billing"));
  const billing = page.getByTestId("billing");
  await expect(billing).toContainText("Gratis");
  await expect(billing).toContainText("Limiten sind in dieser Installation nicht aktiv.");
  await expect(page.getByTestId("plans").getByRole("listitem").filter({ hasText: "CHF 39 pro Monat" })).toBeVisible();
  await expectAccessible(page);

  // privacy (Ich, Meine Daten): personal data download and club deletion with name confirmation
  await page.goto(teamUrl.replace(/\/teams\/.*/, "/me/data"));
  const exported = await page.request.get((await page.getByTestId("export").getAttribute("href"))!);
  expect((await exported.json()).account.name).toBe("Coach Training");
  await page.getByText("Verein löschen", { exact: true }).first().click();
  const del = page.getByRole("form", { name: "Verein löschen" });
  await del.getByLabel("Vereinsname").fill("HC Training");
  await del.getByRole("button", { name: "Verein löschen" }).click();
  await page.getByTestId("confirm-ok").click();
  await expect(page).toHaveURL(/\/onboarding/);
});

import { expect, test } from "@playwright/test";
import { expectAccessible, follow, register, uniqueEmail } from "./helpers";

// M10: training planning (5.7), statistics matrix (5.4), assistant without a model key (5.1)
test("coach plans a session, opens the matrix and the assistant", async ({ page, context }, info) => {
  test.skip(info.project.name !== "chromium", "full flow runs once");
  await register(page, uniqueEmail("coach-data"), "Coach Daten");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Daten");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 2");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;

  // training: a session with two library drills, then the PDF link
  await follow(page, page.getByRole("link", { name: "Training", exact: true }), /\/training$/);
  await page.getByRole("button", { name: "Neue Einheit" }).click();
  const form = page.getByRole("form", { name: "Neue Einheit" });
  const day = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10);
  await form.getByLabel("Datum").fill(day);
  await form.getByLabel("Titel").fill("Abschluss Flügel");
  await form.getByRole("button", { name: "Übung hinzufügen" }).click();
  await form.getByLabel("Übung hinzufügen").selectOption({ index: 1 });
  await form.getByRole("button", { name: "Übung hinzufügen" }).click();
  await expect(form.getByRole("listitem")).toHaveCount(2);
  await form.getByRole("button", { name: "Speichern" }).click();
  await expect(page.getByRole("heading", { name: "Abschluss Flügel" })).toBeVisible();
  const pdf = page.getByRole("link", { name: "PDF" }).first();
  const res = await page.request.get((await pdf.getAttribute("href"))!);
  expect(res.headers()["content-type"]).toContain("application/pdf");
  await expectAccessible(page);

  // calendar link for subscription (the calendar tools fold away under the units)
  await page.getByText("Kalender abonnieren und Termine importieren").click();
  await page.getByRole("button", { name: "Link erzeugen" }).click();
  const url = await page.getByLabel("Kalender abonnieren").inputValue();
  // the link is stored with the request's commit; poll instead of a single read
  await expect.poll(async () => (await page.request.get(url.slice(url.indexOf("/v1/")))).text()).toContain("Abschluss Flügel");

  // matrix: empty team, but the page and its controls work. The team gets an earlier season in
  // the list, so the season choice shows; choosing the current one asks for exactly that season
  const team = await (await page.request.get(`/v1/orgs/${orgId}/teams/${teamId}`)).json();
  const current = team.current_season as { id: string; label: string };
  await page.route(`**/v1/orgs/${orgId}/teams/${teamId}/seasons`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        { ...current, starts_on: "2026-07-01", ends_on: "2027-06-30" },
        { id: "00000000-0000-4000-8000-000000000f25", label: "2025/26", starts_on: "2025-07-01", ends_on: "2026-06-30" },
      ]),
    }),
  );
  const asked: unknown[] = [];
  page.on("request", (r) => r.url().endsWith("/matrix") && r.method() === "POST" && asked.push(r.postDataJSON()));
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);
  await follow(page, page.getByRole("link", { name: "Saison", exact: true }), /\/season$/);
  await follow(page, page.getByRole("link", { name: "Statistik-Matrix" }), /\/matrix$/);
  await expect(page.getByRole("heading", { name: "Statistik-Matrix" })).toBeVisible();
  await expect(page.getByText("Keine Ereignisse für diese Auswahl.")).toBeVisible();
  await page.getByTestId("matrix-seasons").selectOption(current.id);
  await expect.poll(() => asked.at(-1)).toMatchObject({ season_ids: [current.id] });
  await expect(page.getByText("Keine Ereignisse für diese Auswahl.")).toBeVisible();
  // on phones the selection is folded behind one line
  const selection = page.getByRole("button", { name: /^Auswahl/ });
  if (await selection.isVisible()) await selection.click();
  await page.getByRole("button", { name: "Paraden", exact: true }).click();
  await expect(page.getByRole("button", { name: "Paraden", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expectAccessible(page);

  // assistant: no model key in this stack, so the question gets an honest message
  await follow(page, page.getByRole("link", { name: "Frag deine Daten" }), /\/assistant$/);
  await page.getByPlaceholder("Frage zu euren Spielen stellen").fill("Wie oft treffen wir nach einem Timeout?");
  await page.getByRole("button", { name: "Fragen", exact: true }).click();
  await expect(page.getByText("Der Assistent ist in dieser Installation nicht eingerichtet.")).toBeVisible();
  await expectAccessible(page);

  // my dates: the coach has no player profile, so the list is empty
  await page.goto(`/app/${orgId}/schedule`);
  await expect(page.getByText("Keine Termine in den nächsten 30 Tagen.")).toBeVisible();
  expect(teamId).toBeTruthy();
  expect((await context.cookies()).length).toBeGreaterThan(0);
});

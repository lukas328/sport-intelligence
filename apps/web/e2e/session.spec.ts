import { expect, test } from "@playwright/test";
import { expectAccessible, openLibrary, register, uniqueEmail } from "./helpers";

// Addendum 01, A2: own tags and smart playlists, presentation with presenter view and phone remote.
test("video session: tags, smart playlist, presentation with phone remote", async ({ page, context, browser }, info) => {
  test.skip(info.project.name !== "chromium", "full flow runs once");
  const email = uniqueEmail("session");
  await register(page, email, "Coach Video");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Sitzung");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 2");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  const headers = { "x-csrf-token": csrf };
  const match = await (
    await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/matches`, {
      headers,
      data: { opponent_name: "TV Tags", kickoff_at: "2026-11-07T18:00:00+01:00" },
    })
  ).json();
  for (const [i, outcome] of ["goal", "goal", "miss"].entries()) {
    await page.request.post(`/v1/orgs/${orgId}/matches/${match.id}/events`, {
      headers,
      data: { type: "shot", side: "opponent", outcome, t_ms: 60_000 * (i + 1) },
    });
  }

  // own tags and saved searches: behind «Mehr» on Szenen (the event list)
  await openLibrary(page, "Szenen");
  await page.getByTestId("scenes-more").click();
  await expect(page.getByRole("heading", { name: "Szenen suchen" })).toBeVisible();
  const newSet = page.getByRole("form", { name: "Neues Tag-Set" });
  await newSet.getByLabel("Neues Tag-Set").fill("Abwehr");
  await newSet.getByRole("button", { name: "Hinzufügen" }).click();
  const addTag = page.getByRole("form", { name: "Tag zu Abwehr hinzufügen" });
  await addTag.getByLabel("Neuer Tag").fill("Rückzug zu langsam");
  await addTag.getByRole("button", { name: "Hinzufügen" }).click();
  await expect(page.getByTestId("search-count")).toHaveText("3 Szenen");
  await page.getByTestId("search-hits").getByRole("listitem").first().getByRole("button", { name: "Rückzug zu langsam" }).click();
  await expect(page.getByTestId("search-hits").getByRole("listitem").first().getByRole("button", { name: "Rückzug zu langsam" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("complementary").getByRole("button", { name: /Rückzug zu langsam/ }).click();
  await expect(page.getByTestId("search-count")).toHaveText("1 Szene");
  const save = page.getByRole("form", { name: "Suche speichern" });
  await save.getByLabel("Name der gespeicherten Suche").fill("Rückzug");
  await save.getByRole("button", { name: "Suche speichern" }).click();
  await expect(page.getByRole("button", { name: "Rückzug", exact: true })).toBeVisible();
  await expectAccessible(page);

  // presentation: text slide, presenter view, phone remote
  await openLibrary(page, "Zum Zeigen");
  await page.getByLabel("Titel").fill("Video-Sitzung Dienstag");
  await page.getByRole("button", { name: "Neue Sammlung zum Zeigen" }).click();
  await page.waitForURL(/\/presentations\/[^/]+$/);
  for (const title of ["Rückzug", "Abschluss"]) {
    const form = page.getByRole("form", { name: "Notiz" });
    await form.getByLabel("Titel").fill(title);
    await form.getByRole("button", { name: "Hinzufügen" }).click();
    await expect(page.getByTestId("slides")).toContainText(title);
  }
  await expect(page.getByTestId("slides").getByRole("listitem")).toHaveCount(2);
  await expectAccessible(page);
  await page.getByTestId("present").click();
  await expect(page.getByTestId("slide-counter")).toContainText("Eintrag 1 von 2");
  await expect(page.getByTestId("stage")).toContainText("Rückzug");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("slide-counter")).toContainText("Eintrag 2 von 2");
  await page.keyboard.press("ArrowLeft");

  await page.getByRole("button", { name: "Handy-Fernbedienung" }).click();
  const qr = page.getByRole("img", { name: "QR-Code für die Handy-Fernbedienung" });
  await expect(qr).toBeVisible();
  // the phone: same account in a second browser context (cookies copied), opened via the QR link
  const phone = await browser.newContext({ ...test.info().project.use, storageState: await context.storageState() });
  const remote = await phone.newPage();
  const link = await page.getByTestId("remote-link").getAttribute("href");
  expect(link).toContain("/remote?k=");
  await remote.goto(link!);
  const sent = Date.now();
  await remote.getByRole("button", { name: "Weiter" }).click();
  await expect(page.getByTestId("slide-counter")).toContainText("Eintrag 2 von 2");
  const roundTrip = Date.now() - sent;
  console.log(`phone remote round trip ${roundTrip} ms`);
  expect(roundTrip).toBeLessThan(2000); // UI round trip incl. two browsers; server latency shown below
  await expect(page.getByText(/Letzter Befehl: \d+ ms/)).toBeVisible();
  await expectAccessible(remote);
  await phone.close();
});

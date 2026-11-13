import { expect, test } from "@playwright/test";
import { expectAccessible, linkFromMail, register, uniqueEmail } from "./helpers";

// UX test, second delivery: the public entry. The website sends «/?q=…&farbe=…»; the app shows
// the team from handball.ch without an account, an example of the three things, and saves with
// an e-mail and a link. The search needs handball.ch (live or the local cache).
test("entry: from the website's question to Spiele, without a password", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "the entry is for the phone");
  test.setTimeout(240_000);
  await page.goto("/?q=W%C3%A4denswil&farbe=gelb");
  await page.waitForURL(/\/einstieg\?/);
  await expect(page.getByLabel("Wie heisst dein Team?")).toHaveValue("Wädenswil");
  const hits = page.getByTestId("entry-hits");
  await expect(hits.getByRole("button").first()).toBeVisible({ timeout: 60_000 });
  await expectAccessible(page);

  // the own team at once: last result, table, the example of the three things
  await hits.getByRole("button").first().click();
  await expect(page.getByTestId("entry-team")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("radio", { name: "Gelb" })).toBeChecked();
  await expect(page.getByTestId("entry-example")).toContainText("Beispiel aus einem Demo-Spiel");
  await expectAccessible(page);

  // a team without a federation entry goes on by its name; saving is an e-mail and a link
  await page.getByRole("button", { name: "Anderes Team" }).last().click();
  await expect(hits.getByRole("button").first()).toBeVisible({ timeout: 60_000 });
  await page.getByTestId("entry-by-name").click();
  await page.getByLabel("Teamname").fill("HC Einstieg");
  await page.getByRole("button", { name: "Weiter" }).click();
  await expect(page.getByTestId("entry-mail")).toContainText("30 Tage alles gratis");
  await expect(page.getByRole("link", { name: "Nutzungsbedingungen" })).toHaveAttribute("href", /handball-ai\.ch\/de\/agb/);
  const email = uniqueEmail("entry");
  await page.getByLabel("E-Mail").fill(email);
  await page.getByTestId("entry-send").click();
  await expect(page.getByTestId("entry-sent")).toContainText(email);
  await expectAccessible(page);

  const link = await linkFromMail(page, email, "/auth/magic");
  await page.goto(link.replace(/^https?:\/\/[^/]+/, ""));
  await page.waitForURL(/\/teams\/[^/]+\/matches/, { timeout: 90_000 });
  await expect(page.getByRole("main")).toBeVisible();
});

// UX test round 2, N03: after tapping the team there is a sentence and the head at once; a slow
// federation gets an honest state with «Trotzdem speichern».
test("entry: the wait for the team says what happens, slow federation offers saving anyway", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "the entry is for the phone");
  test.setTimeout(180_000);
  await page.goto("/einstieg?q=Meilen&farbe=rot");
  const hits = page.getByTestId("entry-hits");
  await expect(hits.getByRole("button").first()).toBeVisible({ timeout: 60_000 });
  const name = (await hits.getByRole("button").first().locator("span span").first().textContent())!.trim();
  // hold the team's answer back: the federation is slow today
  await page.route(/\/v1\/public\/clubs\/\d+\/teams\/\d+/, async (route) => {
    await new Promise((r) => setTimeout(r, 12_000));
    await route.continue().catch(() => undefined);
  });
  await hits.getByRole("button").first().click();
  await expect(page.getByTestId("entry-loading")).toContainText("Wir holen die Spiele von handball.ch.", { timeout: 2_000 });
  await expect(page.getByRole("heading", { level: 1 })).toContainText(name);
  await expect(page.getByTestId("entry-loading")).toContainText("handball.ch antwortet heute langsam", { timeout: 10_000 });
  await expect(page.getByRole("button", { name: "Trotzdem speichern" })).toBeVisible();
  await page.getByRole("button", { name: "Trotzdem speichern" }).click();
  await expect(page.getByTestId("entry-mail")).toBeVisible();
});

// UX test round 2, N09: a team already in the app says so in the preview; after the link the page
// says what happens and offers a way on instead of a dead end.
test("entry: a team already in the app, request and a way on", async ({ page, browser }, info) => {
  test.skip(info.project.name !== "mobile", "the entry is for the phone");
  test.setTimeout(240_000);
  // someone else has taken the team over already
  await register(page, uniqueEmail("owner"), "Andere Trainerin");
  const hit = (await (await page.request.get("/v1/public/teams?q=Meilen")).json())[0];
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const claim = await page.request.post(`/v1/official/teams/${hit.official_id}/claim`, { headers: { "x-csrf-token": csrf }, data: { club_id: hit.club.id } });
  expect(claim.ok()).toBe(true);

  const ctx = await browser.newContext({ ...info.project.use });
  const hans = await ctx.newPage();
  await hans.goto("/einstieg?q=Meilen&farbe=gelb");
  await hans.getByTestId("entry-hits").getByRole("button").first().click({ timeout: 60_000 });
  await expect(hans.getByTestId("entry-in-app")).toContainText("nutzt Handball Intelligence schon", { timeout: 60_000 });
  await hans.getByTestId("entry-save").click();
  const email = uniqueEmail("hans-taken");
  await hans.getByLabel("E-Mail").fill(email);
  await hans.getByTestId("entry-send").click();
  const link = await linkFromMail(hans, email, "/auth/magic");
  await hans.goto(link.replace(/^https?:\/\/[^/]+/, ""));
  await expect(hans.getByRole("heading", { name: "Anfrage gesendet." })).toBeVisible({ timeout: 90_000 });
  await expect(hans.getByTestId("entry-saving")).toContainText(hit.name);
  await expect(hans.getByTestId("entry-access-ways").getByRole("link", { name: "Anderes Team wählen" })).toBeVisible();
  await hans.getByRole("link", { name: "Bis dahin mit eigenem Team starten" }).click();
  await hans.waitForURL(/\/teams\/[^/]+\/matches/, { timeout: 90_000 });
  await ctx.close();
});

test("an invalid sign-in link leads back to the team choice (UX test N22)", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  const next = encodeURIComponent("/einstieg/speichern?club=330442&team=33555&farbe=rot");
  await page.goto(`/auth/magic?token=kaputt&next=${next}`);
  await expect(page.getByText("Der Link ist ungültig oder abgelaufen.")).toBeVisible();
  const back = page.getByTestId("magic-back");
  await expect(back).toHaveText("Zurück zur Teamwahl");
  await expect(back).toHaveAttribute("href", "/einstieg?club=330442&team=33555&farbe=rot");
  // without a team choice: the search
  await page.goto("/auth/magic?token=kaputt");
  await expect(page.getByTestId("magic-back")).toHaveAttribute("href", "/einstieg");
});

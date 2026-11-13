import { expect, test } from "@playwright/test";
import { expectAccessible, linkFromMail, uniqueEmail } from "./helpers";

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
  await expect(page.getByRole("link", { name: "Nutzungsbedingungen" })).toHaveAttribute("href", /handball-ai\.ch\/agb/);
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

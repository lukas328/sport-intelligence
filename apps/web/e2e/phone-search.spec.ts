import { expect, test } from "@playwright/test";
import { register, uniqueEmail } from "./helpers";

// UX test round 2, B18/N08: on the phone «Suchen» is in the top bar again (the magnifier, the word
// when there is room), and the tab Szenen opens with the cursor in the search.
test("phone: search from the top bar and from the tab Szenen", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "the phone's top bar");
  await register(page, uniqueEmail("phone-search"), "Coach Suche");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Suche");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);

  const search = page.getByTestId("search-open-compact");
  await expect(search).toBeVisible();
  await expect(search).toHaveAccessibleName("Suchen");
  await search.click();
  await page.waitForURL(/\/scenes\?focus=1/);
  await expect(page.getByTestId("scene-search")).toBeFocused();

  await page.goto(page.url().replace(/\/scenes.*$/, "/matches"));
  await page.getByRole("navigation", { name: "Hauptnavigation" }).getByRole("link", { name: "Szenen" }).click();
  await page.waitForURL(/\/scenes\?focus=1/);
  await expect(page.getByTestId("scene-search")).toBeFocused();
});

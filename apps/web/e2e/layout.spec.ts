import { expect, test, type Page } from "@playwright/test";
import { register, uniqueEmail } from "./helpers";

async function noHorizontalScroll(page: Page) {
  await page.waitForTimeout(300);
  const { scroll, width } = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    width: document.documentElement.clientWidth,
  }));
  expect(scroll, `${page.url()} is wider than the screen`).toBeLessThanOrEqual(width);
}

test("no horizontal scrolling on phones", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "phone viewport only");
  await register(page, uniqueEmail("layout"), "Coach Mobile");
  await page.getByLabel("Vereinsname").fill("HC Schmal");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Junioren U15 Leistungsgruppe");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const teamUrl = page.url().replace(/(\/teams\/[^/?#]+).*/, "$1");
  for (const path of ["", "/matches", "/playlists", "/plays", "/season", "/assignments"]) {
    await page.goto(teamUrl + path);
    await noHorizontalScroll(page);
  }
  await page.goto(`${teamUrl}/matches`);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Mit Einem Sehr Langen Vereinsnamen");
  await page.getByRole("button", { name: "Spiel anlegen" }).click();
  await page.waitForURL(/\/matches\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await noHorizontalScroll(page);
  await page.goto(page.url() + "/live");
  await expect(page.getByTestId("live")).toBeVisible();
  await noHorizontalScroll(page);
  await page.goto(teamUrl.replace(/\/teams\/.*/, "/settings"));
  await noHorizontalScroll(page);
});

import { expect, test, type Page } from "@playwright/test";
import { register, uniqueEmail } from "./helpers";

async function noHorizontalScroll(page: Page) {
  // old addresses redirect (settings to club): measure the page that stays
  await page.waitForLoadState("networkidle");
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
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Schmal");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Junioren U15 Leistungsgruppe");
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

test("large text at 300 px: the team name in the top bar stays readable (UX test A01)", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("a01"), "Coach Gross");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Wädenswil");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("SG Wädenswil/Horgen");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  await page.setViewportSize({ width: 300, height: 700 });
  await page.reload();
  const bar = page.locator("[data-frame=top] .lg\\:hidden");
  const name = bar.getByText(/SG Wädenswil/);
  await expect(name).toBeVisible();
  // the name has room: at least two words in a line, at most two lines
  const box = (await name.boundingBox())!;
  expect(box.width).toBeGreaterThanOrEqual(100);
  expect(box.height).toBeLessThanOrEqual(45);
  // the rest gave way: the word «Video» is gone, the plus stays as a 44 px button
  const upload = bar.getByTestId("upload-video-compact");
  if (await upload.count()) {
    await expect(upload).toHaveAccessibleName("Video hochladen");
    expect((await upload.boundingBox())!.width).toBeLessThanOrEqual(46);
  }
  await noHorizontalScroll(page);
});

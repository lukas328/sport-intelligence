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
  // the magnifier gave way: the tab Szenen is also the search, by its name
  await expect(page.getByRole("link", { name: "Szenen und Suche" })).toBeVisible();
  await noHorizontalScroll(page);
});

test("unknown match, team and collection addresses answer 404 (UX test N18)", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("n18"), "Coach Adresse");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Adresse");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const org = page.url().match(/\/app\/([^/]+)/)![1];
  const none = "00000000-0000-0000-0000-000000000000";
  for (const path of [`matches/${none}`, "matches/kaputt", `collections/${none}`, `teams/${none}/matches`, "nichts"]) {
    const res = await page.goto(`/app/${org}/${path}`);
    expect(res?.status(), path).toBe(404);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Diese Seite gibt es nicht");
  }
  // the club start still opens
  expect((await page.goto(`/app/${org}`))?.status()).toBe(200);
});

test("a club without video: Szenen says one sentence and the way to the video (UX test B28)", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("b28"), "Coach Leer");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Leer");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  await page.goto(page.url().replace(/(\/teams\/[^/?#]+).*/, "$1/scenes"));
  const empty = page.getByTestId("scenes-empty");
  await expect(empty).toContainText("Szenen gibt es nach dem ersten Video.");
  await expect(empty.getByRole("link", { name: "Video hochladen" })).toBeVisible();
  await expect(page.getByTestId("scene-search")).toHaveCount(0);
  await expect(page.getByText(/0 Szenen aus 0 Spielen/)).toHaveCount(0);
});

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { clubByHand, expectAccessible, follow, matchMenu, openAnalysis, openMatches, register, uniqueEmail } from "./helpers";

const REPORT = fileURLToPath(new URL("./fixtures/paper-report.json", import.meta.url));

test("paper report: import, overview, match report, shots", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  JSON.parse(readFileSync(REPORT, "utf8")); // fixture stays valid JSON
  await register(page, uniqueEmail("paper"), "Coach Papier");
  await clubByHand(page, "HC Papier");
  await page.getByLabel("Teamname").fill("Damen 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);

  // the paper import is no longer offered in the app (K19), its API stays: the data comes that way
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const imported = await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/paper-reports`, {
    headers: { "x-csrf-token": csrf },
    multipart: { file: { name: "paper-report.json", mimeType: "application/json", buffer: readFileSync(REPORT) } },
  });
  expect(imported.ok()).toBeTruthy();
  await page.reload();
  await page.getByRole("link", { name: /TV Papierdorf/ }).first().click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("TV Papierdorf");
  await expect(page.getByTestId("score")).toHaveText("5:4");
  await matchMenu(page);
  const pdf = await page.request.get((await page.getByTestId("pdf").getAttribute("href"))!);
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
  expect((await pdf.body()).subarray(0, 4).toString()).toBe("%PDF");
  await page.getByRole("menuitem", { name: /Gegner-Profil/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "TV Papierdorf" })).toBeVisible();
  await expect(page.getByText("Unsere Bilanz gegen sie: 1 Sieg")).toBeVisible();
  await expect(page.getByTestId("opponent-tiles")).toBeVisible();
  await expectAccessible(page);
  // back where the coach came from: the match
  await page.getByRole("link", { name: "Zurück" }).click();
  await expect(page.getByTestId("score")).toHaveText("5:4");

  // Tab Spiel below the three things (UX test B08): the telegram from the report, no video yet
  await page.getByRole("tab", { name: "Spiel", exact: true }).click();
  await expect(page.getByTestId("telegram")).toContainText("5:4");
  await expect(page.getByTestId("no-video")).toContainText("Kein Video");
  // without video what works today stands first: the Spielkarte for the chat (review R39)
  await expect(page.getByTestId("today-block")).toContainText("Spielkarte für den Teamchat");
  await openAnalysis(page, "Übersicht");
  const table = page.getByTestId("comparison");
  await expect(table.getByRole("row", { name: /^Tore(?! pro)/ })).toContainText("5");
  // UX test B07: a report without goal times has no runs and no course; no xG, no possession
  const main = page.getByRole("main");
  await expect(main).not.toContainText("in Folge");
  await expect(main).not.toContainText("Bester Lauf");
  await expect(main).not.toContainText("xG");
  await expect(main).not.toContainText("Ballbesitz");
  await expect(main).not.toContainText("Papierbericht");
  await expectAccessible(page);
  // every number opens the events behind it
  // «Mehr zum Spiel» has no second list of three things any more (UX test B08)
  await expect(page.getByTestId("insights")).toHaveCount(0);
  await table.getByRole("button", { name: "Tore Damen 1" }).click();
  await expect(page.getByTestId("event-list").getByRole("listitem")).toHaveCount(5);

  await openAnalysis(page, "Spielbericht");
  await expect(page.getByText("Anna Muster").first()).toBeVisible();
  await expectAccessible(page);

  await openAnalysis(page, "Würfe");
  // Zahlen stacks the sheets: the shots section has its own goal grid
  await expect(page.getByRole("region", { name: "Würfe" }).getByTestId("goal-grid")).toBeVisible();
  await expectAccessible(page);

  // goalkeeper module: the sheet's keeper with saves and goals against by zone
  await openAnalysis(page, "Torhüter");
  // one row per goalkeeper in a match-sheet table
  const keepers = page.getByTestId("keeper-table");
  await expect(keepers).toContainText("Paraden");
  const keeper = keepers.getByRole("row", { name: /Mia Tor/ });
  await expect(keeper.getByText("6", { exact: true })).toBeVisible();
  await expectAccessible(page);

  // season view across matches (Saison is in the main navigation; going back would reopen the
  // report dialog the match was imported from)
  await openMatches(page, "Saison");
  // the number of matches is part of the stage line now, the strip holds the per-match figures
  await expect(page.getByRole("main")).toContainText("nach einem Spiel");
  // the figures, the bests and all matches sit behind «Mehr zur Saison»
  await page.getByTestId("season-more").locator("summary").click();
  await expect(page.getByTestId("season-tiles")).toContainText("Tore pro Spiel");
  await expect(page.getByTestId("season-matches")).toContainText("TV Papierdorf");
  // the course of the goal difference is drawn once, at the top (review R26), not again in here
  await expect(page.getByTestId("season-more").getByRole("img", { name: "Tordifferenz pro Spiel" })).toHaveCount(0);
  await expectAccessible(page);
});

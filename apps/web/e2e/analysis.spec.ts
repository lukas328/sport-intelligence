import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { expectAccessible, register, uniqueEmail } from "./helpers";

const REPORT = fileURLToPath(new URL("./fixtures/paper-report.json", import.meta.url));

test("paper report: import, overview, match report, shots", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  JSON.parse(readFileSync(REPORT, "utf8")); // fixture stays valid JSON
  await register(page, uniqueEmail("paper"), "Coach Papier");
  await page.getByLabel("Vereinsname").fill("HC Papier");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Damen 1");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.getByRole("link", { name: "Spiele" }).first().click();

  await page.getByTestId("paper-file").setInputFiles(REPORT);
  // goalkeeper zones carry one unknown shooter: the import reports it and stays on the list
  await expect(page.getByText("Hinweise")).toBeVisible();
  await page.getByRole("link", { name: /TV Papierdorf/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("TV Papierdorf");
  await expect(page.getByTestId("score")).toHaveText("5:4");

  await page.getByRole("tab", { name: "Übersicht" }).click();
  const table = page.getByTestId("comparison");
  await expect(table.getByRole("row", { name: /^Tore/ })).toContainText("5");
  await expectAccessible(page);
  // every number opens the events behind it
  await table.getByRole("button", { name: "Tore Damen 1" }).click();
  await expect(page.getByTestId("event-list").getByRole("listitem")).toHaveCount(5);

  await page.getByRole("tab", { name: "Matchreport" }).click();
  await expect(page.getByText("Anna Muster").first()).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("tab", { name: "Würfe" }).click();
  await expect(page.getByTestId("goal-grid")).toBeVisible();
  await expectAccessible(page);

  // goalkeeper module: the sheet's keeper with saves and goals against by zone
  await page.getByRole("tab", { name: "Torhüter" }).click();
  const keeper = page.getByTestId("keeper-card").filter({ hasText: "Mia Tor" });
  await expect(keeper).toContainText("Paraden");
  await expect(keeper.getByText("6", { exact: true })).toBeVisible();
  await expectAccessible(page);
});

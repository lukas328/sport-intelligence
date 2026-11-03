import { expect, test } from "@playwright/test";
import { expectAccessible, register, uniqueEmail } from "./helpers";

test("play library: template, edit on the board, animate, save, find", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("tac"), "Coach Taktik");
  await page.getByLabel("Vereinsname").fill("HC Taktik");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 2");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();

  await page.getByRole("link", { name: "Spielzüge" }).click();
  await expect(page.getByText("Noch keine Spielzüge.")).toBeVisible();
  await page.getByRole("searchbox").fill("5-1");
  await page.getByRole("link", { name: "Vorlage verwenden: Abwehr 5:1" }).click();
  await expect(page.getByLabel("Name")).toHaveValue("Abwehr 5:1");
  const board = page.getByTestId("tactics-board");
  await expect(board.locator("[data-testid^=token-]")).toHaveCount(13);
  await expectAccessible(page);

  // keyboard: the advanced defender steps out by 2 m
  const d6 = page.getByTestId("token-d6");
  await d6.focus();
  const before = await d6.getAttribute("transform");
  await page.keyboard.press("Shift+ArrowLeft");
  await expect(d6).not.toHaveAttribute("transform", before!);

  // a run arrow with the pointer, then a second phase that follows it
  await page.getByRole("button", { name: "Laufweg" }).click();
  await board.scrollIntoViewIfNeeded();
  const box = (await board.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.3, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.3, { steps: 4 });
  await page.mouse.up();
  await expect(board.locator("path[marker-end]")).toHaveCount(1);
  await page.getByRole("button", { name: "+ Phase" }).click();
  await expect(page.getByRole("button", { name: "2", exact: true })).toHaveAttribute("aria-current", "step");
  await page.getByLabel("Notiz zur Phase").fill("Ballseite verschieben");
  await page.getByRole("button", { name: "Abspielen" }).click();
  await expect(page.getByRole("button", { name: "Pause" })).toBeVisible();

  await page.getByLabel("Stichworte (mit Komma getrennt)").fill("5:1, offensiv");
  await page.getByRole("button", { name: "Spielzug speichern" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Abwehr 5:1" })).toBeVisible();
  await expect(page.getByRole("button", { name: "2", exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Spielzüge" }).first().click();
  await expect(page.getByTestId("play-list")).toContainText("Abwehr 5:1");
  await page.getByRole("searchbox").fill("offensiv");
  await expect(page.getByTestId("play-list")).toContainText("2 Phasen");
  await expectAccessible(page);
});

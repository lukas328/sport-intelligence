import { expect, test } from "@playwright/test";
import { expectAccessible, register, uniqueEmail } from "./helpers";

test("operator backoffice is hidden for clubs and works for operators", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("club"), "Coach Normal");
  const res = await page.goto("/ops");
  expect(res?.status()).toBe(404);

  await page.context().clearCookies();
  await register(page, `ops-${Date.now()}@ops-e2e.ch`, "Operatorin");
  await page.goto("/ops");
  await expect(page.getByRole("heading", { level: 1, name: "Backoffice" })).toBeVisible();
  await expect(page.getByTestId("ops-tiles")).toContainText("Vereine");
  await expect(page.getByTestId("ops-orgs")).toBeVisible();
  await expectAccessible(page);
});

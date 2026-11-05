import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("home page renders the court and links to status", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Video hochladen");
  // the court frames the stage as decoration (aria-hidden); the call to action is what counts
  await expect(page.getByRole("link", { name: "Jetzt starten" })).toBeVisible();
  const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag22aa"]).analyze();
  expect(axe.violations).toEqual([]);
});

test("status page shows all services ok", async ({ page }) => {
  await page.goto("/status");
  await expect(page.getByTestId("overall-status")).toHaveAttribute("data-state", "ok");
  for (const name of ["database", "redis", "storage"]) {
    await expect(page.getByTestId(`component-${name}`)).toContainText("OK");
  }
  const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag22aa"]).analyze();
  expect(axe.violations).toEqual([]);
});

test("web liveness endpoint", async ({ request }) => {
  const r = await request.get("/api/healthz");
  expect(r.ok()).toBeTruthy();
});

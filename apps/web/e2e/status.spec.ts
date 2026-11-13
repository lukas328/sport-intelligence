import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("home page: without a session «/» is the public entry", async ({ page }) => {
  // the marketing lives on the website; the app's root asks for the team (UX test, second delivery)
  await page.goto("/");
  await page.waitForURL(/\/einstieg/);
  await expect(page.getByLabel("Wie heisst dein Team?")).toBeVisible();
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

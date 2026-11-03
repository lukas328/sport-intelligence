import { expect, test } from "@playwright/test";
import { expectAccessible, register, uniqueEmail } from "./helpers";

test("live tagging courtside: clock, buttons, offline queue, sync", async ({ page, context }, info) => {
  test.skip(info.project.name !== "chromium", "runs once (service worker, offline)");
  await register(page, uniqueEmail("live"), "Coach Live");
  await page.getByLabel("Vereinsname").fill("HC Live");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Damen 2");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const teamUrl = page.url();
  const [, orgId, teamId] = teamUrl.match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;

  // roster player via the API (same session and CSRF cookie as the browser)
  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  const team = await (await page.request.get(`/v1/orgs/${orgId}/teams/${teamId}`)).json();
  await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/seasons/${team.current_season.id}/roster`, {
    headers: { "x-csrf-token": csrf },
    data: { first_name: "Lina", last_name: "Muster", jersey_number: 11 },
  });

  await page.getByRole("link", { name: "Spiele" }).first().click();
  await page.getByLabel("Gegner", { exact: true }).fill("TV Halle");
  await page.getByRole("button", { name: "Spiel anlegen" }).click();
  await page.getByTestId("live-link").click();
  await expect(page.getByTestId("live")).toBeVisible();
  await expect(page.getByTestId("live-score")).toHaveText("0:0");
  await expectAccessible(page);

  await page.getByRole("button", { name: "Start" }).click();
  await expect.poll(async () => page.getByTestId("live-clock").textContent()).not.toBe("0:00");
  await page.getByRole("button", { name: /11\s*Lina/ }).click();
  await page.getByRole("button", { name: "Tor", exact: true }).click();
  await expect(page.getByTestId("live-score")).toHaveText("1:0");
  await expect(page.getByTestId("sync-state")).toHaveText("Alles gespeichert");

  // the hall Wi-Fi drops: events queue up, the page even reloads from the service worker
  await page.waitForFunction(async () => (await caches.open("hb-live-v1").then((c) => c.match(location.href))) !== undefined);
  await context.setOffline(true);
  await page.getByRole("button", { name: "Gegentor" }).click();
  await page.getByRole("button", { name: "Fehlwurf" }).first().click();
  await expect(page.getByTestId("sync-state")).toContainText("2");
  await page.reload();
  await expect(page.getByTestId("live")).toBeVisible();
  await expect(page.getByTestId("live-log").getByRole("listitem")).toHaveCount(2);
  await context.setOffline(false);
  await expect(page.getByTestId("sync-state")).toHaveText("Alles gespeichert", { timeout: 20_000 });

  const match = page.url().match(/matches\/([^/]+)\/live/)![1];
  const events = await (await page.request.get(`/v1/orgs/${orgId}/matches/${match}/events`)).json();
  expect(events).toHaveLength(3);
  expect(events.filter((e: { outcome: string }) => e.outcome === "goal")).toHaveLength(2);
});

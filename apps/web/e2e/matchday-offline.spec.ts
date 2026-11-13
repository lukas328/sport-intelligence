import { expect, test } from "@playwright/test";
import { register, uniqueEmail } from "./helpers";

// UX test round 2, N01 and N02: the Spieltag opens again without network after a reload, and a
// mark made offline is stored once when the network is back.
test("matchday: reload without network, offline mark stored once", async ({ page, context }, info) => {
  test.skip(info.project.name !== "mobile", "courtside is the phone");
  test.setTimeout(180_000);
  await register(page, uniqueEmail("offline"), "Coach Offline");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Offline");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  const match = await (
    await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/matches`, {
      headers: { "x-csrf-token": csrf },
      data: { opponent_name: "TV Funkloch", kickoff_at: new Date().toISOString() },
    })
  ).json();

  await page.goto(`/app/${orgId}/matches/${match.id}/matchday`);
  await page.getByRole("button", { name: /^Tor wir/ }).click();
  await expect(page.getByText("Alles hochgeladen")).toBeVisible({ timeout: 15_000 });
  // the service worker is there and has the page
  await expect.poll(async () => page.evaluate(async () => (await navigator.serviceWorker.getRegistrations()).length), { timeout: 20_000 }).toBe(1);
  await expect.poll(async () => page.evaluate(async () => (await (await caches.open("hb-live-v1")).keys()).length), { timeout: 20_000 }).toBeGreaterThan(3);

  // in the hall without signal: reload, the page and the marks are there, a new mark waits
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole("button", { name: /^Gute Aktion/ })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("marks-log").getByRole("listitem")).toHaveCount(1);
  await page.getByRole("button", { name: /^Gute Aktion/ }).click();
  await expect(page.getByTestId("marks-log").getByRole("listitem")).toHaveCount(2);

  // back online: uploaded once, also after a reload and on the server
  await context.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(page.getByText("Alles hochgeladen")).toBeVisible({ timeout: 30_000 });
  await page.reload();
  await expect(page.getByTestId("marks-log").getByRole("listitem")).toHaveCount(2);
  await expect(page.getByTestId("marks-log").getByText("Gute Aktion")).toHaveCount(1);
  const listed = await (await page.request.get(`/v1/orgs/${orgId}/matches/${match.id}/marks`)).json();
  expect(listed.marks.filter((m: { key: string }) => m.key === "good")).toHaveLength(1);
});

// UX test round 2, N14: the match clock runs on the phone, the small keys mark, the last mark is
// taken back (also on the server).
test("matchday: match clock, small keys, take back", async ({ page, context }, info) => {
  test.skip(info.project.name !== "mobile", "courtside is the phone");
  test.setTimeout(120_000);
  await register(page, uniqueEmail("clock"), "Coach Uhr");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Uhr");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  const match = await (
    await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/matches`, { headers: { "x-csrf-token": csrf }, data: { opponent_name: "TV Uhr", kickoff_at: new Date().toISOString() } })
  ).json();
  await page.goto(`/app/${orgId}/matches/${match.id}/matchday`);
  await expect(page.getByTestId("match-clock")).toHaveText("00:00");
  await page.getByTestId("clock-toggle").click();
  await expect(page.getByTestId("match-clock")).not.toHaveText("00:00", { timeout: 5_000 });
  await expect(page.getByTestId("share-matchday")).toBeVisible();

  await page.getByRole("button", { name: "2 Minuten" }).click();
  await page.getByRole("button", { name: "Time-out" }).click();
  await expect(page.getByTestId("marks-log").getByRole("listitem")).toHaveCount(2);
  // each entry with the game time of the clock, the phone's time only small (UX test A03)
  await expect(page.getByTestId("marks-log").getByRole("listitem").first()).toContainText(/^00:0\d/);
  await expect(page.getByText("Alles hochgeladen")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("take-back").click();
  await expect(page.getByTestId("marks-log").getByRole("listitem")).toHaveCount(1);
  await expect.poll(async () => (await (await page.request.get(`/v1/orgs/${orgId}/matches/${match.id}/marks`)).json()).marks.map((m: { key: string }) => m.key)).toEqual(["two_min"]);
  // the clock keeps its time over a reload
  await page.reload();
  await expect(page.getByTestId("match-clock")).not.toHaveText("00:00");
});

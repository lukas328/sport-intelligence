import { expect, test } from "@playwright/test";
import { clubByHand, register, uniqueEmail } from "./helpers";

// UX test round 2, B18/N08: on the phone «Suchen» is in the top bar again (the magnifier, the word
// when there is room), and the tab Szenen opens with the cursor in the search.
test("phone: search from the top bar and from the tab Szenen", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "the phone's top bar");
  await register(page, uniqueEmail("phone-search"), "Coach Suche");
  await clubByHand(page, "HC Suche");
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  // Szenen has its search once a video is there (K8): a match with a started upload
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const headers = { "x-csrf-token": (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value };
  const match = await (await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/matches`, { headers, data: { opponent_name: "TV Suche", kickoff_at: "2026-11-07T18:00:00+01:00" } })).json();
  await page.request.post(`/v1/orgs/${orgId}/matches/${match.id}/videos`, { headers, data: { filename: "suche.mp4", size_bytes: 6_000_000, content_type: "video/mp4", role: "main" } });
  await page.reload();

  const search = page.getByTestId("search-open-compact");
  await expect(search).toBeVisible();
  await expect(search).toHaveAccessibleName("Suchen");
  await search.click();
  await page.waitForURL(/\/scenes\?focus=1/);
  await expect(page.getByTestId("scene-search")).toBeFocused();

  await page.goto(page.url().replace(/\/scenes.*$/, "/matches"));
  await page.getByRole("navigation", { name: "Hauptnavigation" }).getByRole("link", { name: "Szenen" }).click();
  await page.waitForURL(/\/scenes\?focus=1/);
  await expect(page.getByTestId("scene-search")).toBeFocused();
});

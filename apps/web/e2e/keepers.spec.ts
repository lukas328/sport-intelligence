import { expect, test } from "@playwright/test";
import { clubByHand, register, uniqueEmail } from "./helpers";

/** A team has more than one goalkeeper: the block «Wer steht im Tor?» stays open for every keeper
 * and folds into one line after «Fertig» (Lukas, 17.11.: it closed after the first keeper). */
test("squad: mark two goalkeepers, take one out again", async ({ page, context }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("keepers"), "Coach Tor");
  await clubByHand(page, "HC Torlinie");
  await page.getByLabel("Teamname").fill("Herren 2");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  const team = await (await page.request.get(`/v1/orgs/${orgId}/teams/${teamId}`)).json();
  for (const [first, number] of [["Mia", 1], ["Lea", 12], ["Noa", 7]] as const) {
    const r = await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/seasons/${team.current_season.id}/roster`, {
      headers: { "x-csrf-token": csrf },
      data: { first_name: first, last_name: "Muster", jersey_number: number },
    });
    expect(r.ok()).toBeTruthy();
  }
  await page.goto(`/app/${orgId}/teams/${teamId}`);
  const block = page.getByTestId("mark-keepers");
  await expect(block.getByRole("heading", { name: "Wer steht im Tor?" })).toBeVisible();

  const mia = block.getByRole("button", { name: "Mia Muster im Tor" });
  const lea = block.getByRole("button", { name: "Lea Muster im Tor" });
  await mia.click();
  await expect(mia).toHaveAttribute("aria-pressed", "true");
  // the block stays open for the second keeper
  await lea.click();
  await expect(lea).toHaveAttribute("aria-pressed", "true");
  await block.getByRole("button", { name: "Noa Muster im Tor" }).click();
  await expect(block.getByRole("button", { name: "Noa Muster im Tor" })).toHaveAttribute("aria-pressed", "true");
  // a second tap takes someone out again
  await block.getByRole("button", { name: "Noa Muster im Tor" }).click();
  await expect(block.getByRole("button", { name: "Noa Muster im Tor" })).toHaveAttribute("aria-pressed", "false");

  await block.getByTestId("keepers-done").click();
  await expect(page.getByTestId("mark-keepers")).toContainText("2 Torhüter eingetragen.");
  await page.reload();
  await expect(page.getByTestId("mark-keepers")).toContainText("2 Torhüter eingetragen.");
  await page.getByTestId("keepers-open").click();
  await expect(page.getByRole("button", { name: "Mia Muster im Tor" })).toHaveAttribute("aria-pressed", "true");
});

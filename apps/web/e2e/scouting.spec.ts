import { expect, test } from "@playwright/test";
import { clubByHand, register, uniqueEmail } from "./helpers";

// K3, UI check 20.11.: the form for an observed match asks who plays at home, by default the first
// named team (the observed opponent); the head and every pairing follow it
test("observed match: the form asks for the home team", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("scout"), "Coach Beobachten");
  await clubByHand(page, "HC Beobachter");
  await page.getByLabel("Teamname").fill("Herren 3");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  await page.goto(`/app/${orgId}/teams/${teamId}/matches`);

  // a new team has no match yet: «Video hochladen», then «Video vom Gegner»
  await page.getByRole("link", { name: "Video hochladen" }).first().click();
  await page.getByTestId("upload-scouting").click();
  const form = page.getByTestId("scouting-form");
  await form.getByTestId("scouting-opponent").fill("HC Beobachtet");
  await form.getByTestId("scouting-other").fill("TV Dritte");
  const home = form.getByTestId("scouting-home");
  await expect(home).toContainText("Wer spielt zu Hause?");
  await expect(home).toContainText("TV Dritte");
  await expect(home.getByTestId("scouting-home-opponent")).toBeChecked();
  await form.getByRole("group", { name: "Welche Farbe trägt HC Beobachtet?" }).getByRole("radio", { name: "Blau" }).check({ force: true });
  await form.getByRole("group", { name: "Welche Farbe trägt TV Dritte?" }).getByRole("radio", { name: "Rot" }).check({ force: true });
  await form.getByTestId("scouting-submit").click();
  await page.waitForURL(/\/matches\/[^/?#]+\?tab=video/);
  const matchId = page.url().match(/\/matches\/([^/?#]+)/)![1];

  // stored: the other team (the data's own side) plays away
  const match = await (await page.request.get(`/v1/orgs/${orgId}/matches/${matchId}`)).json();
  expect(match.is_home).toBe(false);
  await page.goto(`/app/${orgId}/matches/${matchId}`);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/HC Beobachtet.*gegen.*TV Dritte/);
});

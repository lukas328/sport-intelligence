import { expect, test } from "@playwright/test";
import { withShotReview, type ShotReviewBody } from "../src/lib/shot-candidates";
import { shotList } from "./fixtures/shots";
import { MATCH_VIDEO } from "./global-setup";
import { expectAccessible, follow, register, uniqueEmail } from "./helpers";

// Shot review beside the video (Würfe): the video is uploaded for real, the candidate list and the
// review answers come from a recorded list (fixtures/shots.ts) kept in step like the API keeps it.
test("shot review: Enter takes the report's entry, 1 + G says a goal, X no shot, U undoes", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(300_000);

  let list = shotList();
  const reviews: ShotReviewBody[] = [];
  await page.route("**/v1/orgs/*/matches/*/shot-candidates", (route) =>
    route.fulfill({ contentType: "application/json", body: JSON.stringify(list) }),
  );
  await page.route("**/v1/orgs/*/matches/*/goal-candidates/*/review", (route) => {
    const id = route.request().url().split("/").at(-2)!;
    const body = route.request().postDataJSON() as ShotReviewBody;
    reviews.push(body);
    list = withShotReview(list, id, body);
    return route.fulfill({ contentType: "application/json", body: JSON.stringify(list.candidates.find((c) => c.id === id)) });
  });

  await register(page, uniqueEmail("shots"), "Coach Würfe");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Würfe");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Testdorf");
  await page.getByRole("button", { name: "Spiel anlegen" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("TV Testdorf");
  await page.getByTestId("video-file").setInputFiles(MATCH_VIDEO);
  await expect(page.getByTestId("player")).toBeVisible({ timeout: 180_000 });

  // the tool sits beside the events once there are shot candidates; with a report, its moments first
  await page.getByTestId("step-shots").click();
  const panel = page.getByTestId("shot-candidates");
  await expect(panel.getByRole("heading", { name: "Würfe prüfen" })).toBeVisible();
  await expect(page.getByTestId("shot-candidates-report")).toContainText("Matchbericht: 24 Würfe, 0 im Video bestätigt, 1 vorgeschlagen, 2 ohne Stelle im Video.");
  await expect(page.getByTestId("shot-candidates-report")).toContainText("21 liegen ausserhalb des Videos.");
  await expect(page.getByTestId("shot-accept")).toContainText("Parade, #14 Kurt Beispiel (TV Testdorf)");
  await expectAccessible(page);

  // Enter on the moment takes the report's entry (player and outcome pinned to the video)
  const rows = panel.getByTestId("shot-candidate-row");
  await expect(rows).toHaveCount(1);
  await rows.first().focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("shot-candidates-said")).toContainText("1. HZ 12:45: Parade, #14 Kurt Beispiel (TV Testdorf) aus dem Matchbericht.");
  expect(reviews.at(-1)).toEqual({ status: "confirmed" });

  // the report's moments are done: the open ones follow; a team first, then the outcome
  await expect(rows).toHaveCount(2);
  await rows.first().focus();
  await page.keyboard.press("g");
  await expect(panel.getByText("Erst das Team wählen: 1 oder 2.")).toBeVisible();
  await page.keyboard.press("1");
  await page.keyboard.press("g");
  await expect(page.getByTestId("shot-candidates-said")).toContainText("1. HZ 12:52: Tor Herren 1.");
  expect(reviews.at(-1)).toEqual({ status: "confirmed", side: "own", outcome: "goal" });

  // X: not a shot; U takes it back
  await expect(rows).toHaveCount(1);
  await rows.first().focus();
  await page.keyboard.press("x");
  await expect(page.getByTestId("shot-candidates-said")).toContainText("1. HZ 13:00: Kein Wurf.");
  await expect(panel.getByText("Alle Würfe sind geprüft.")).toBeVisible();
  await panel.getByRole("button", { name: "Rückgängig", exact: true }).click();
  await expect(rows).toHaveCount(1);
  expect(reviews.at(-1)).toEqual({ status: null });
  await expectAccessible(page);
});

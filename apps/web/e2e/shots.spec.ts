import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { withShotReview, type ShotReviewBody } from "../src/lib/shot-candidates";
import { shotList } from "./fixtures/shots";
import { MATCH_VIDEO } from "./global-setup";
import { expectAccessible, follow, register, uniqueEmail } from "./helpers";

// Shot review beside the video (Würfe): the video is uploaded for real, the candidate list and the
// review answers come from a recorded list (fixtures/shots.ts) kept in step like the API keeps it.
test("court from the hall: Passt moves on; shot review: Enter takes the report entry, 1 + G, X, undo", async ({ page }, info) => {
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

  // the court was carried over from an earlier video of the same hall and waits for a look
  let courtSource = "heuristic";
  const H = [[30.9, 37.6, 21.8], [0, 7.35, 470.6], [0, 0.0588, 1]];
  const logo = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "fixtures", "logo.png"));
  await page.route("**/v1/orgs/*/videos/*/panorama", (route) => route.fulfill({ contentType: "image/png", body: logo }));
  await page.route("**/v1/orgs/*/videos/*/calibration/confirm", (route) => {
    courtSource = "user_correction";
    return route.fulfill({ contentType: "application/json", body: JSON.stringify({ calibration_id: "c", source: courtSource }) });
  });
  await page.route("**/v1/orgs/*/videos/*/analysis", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: "ready",
        calibration: { homography: H, image_size: [1280, 720], confidence: 0.8, reprojection_px: 2, source: courtSource, created_at: "2026-11-09T10:00:00Z" },
        calibration_info: { method: "hall", hall_match: "floor" },
        camera: "fixed",
        panorama: { width: 1280, height: 720 },
        hall: { name: "Sporthalle Seefeld", source: "match", calibrated_videos: 2 },
        tracks: [], chunk_ms: null, chunks: null, fps: 50, detector: "yolo", elapsed_s: 40, formations: [], auto_events: null, error: null, needs_calibration: false,
      }),
    }),
  );

  await register(page, uniqueEmail("shots"), "Coach Würfe");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Würfe");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Testdorf");
  await page.getByRole("button", { name: "Spiel anlegen" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("TV Testdorf");
  await page.getByTestId("video-file").setInputFiles(MATCH_VIDEO);
  await expect(page.getByTestId("player")).toBeVisible({ timeout: 180_000 });

  // court from the hall: one look at the orange lines, "Passt", and on to the next open step
  await page.getByTestId("step-court").click();
  await expect(page.getByText("Spielfeld aus einem früheren Video derselben Halle übernommen (Sporthalle Seefeld). Liegen die orangen Linien")).toBeVisible();
  await expect(page.getByTestId("court-preview")).toBeVisible();
  await expect(page.getByTestId("step-court")).toContainText("bitte prüfen");
  await page.getByTestId("court-confirm").click();
  await expect(page.getByTestId("step-kickoff")).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId("step-court")).toContainText("bestätigt");

  // the tool sits beside the events once there are shot candidates; with a report, its moments first
  await page.getByTestId("step-shots").click();
  const panel = page.getByTestId("shot-candidates");
  await expect(panel.getByRole("heading", { name: "Würfe prüfen" })).toBeVisible();
  // the report against the video as one row of counts
  const report = page.getByTestId("shot-candidates-report");
  await expect(report).toContainText("Spielbericht: 24 Würfe");
  for (const [label, n] of [["im Video bestätigt", "0"], ["vorgeschlagen", "1"], ["ohne Stelle im Video", "2"], ["ausserhalb des Videos", "21"]] as const) {
    await expect(report.locator("dl > div").filter({ has: page.getByText(label, { exact: true }) }).locator("dd")).toHaveText(n);
  }
  await expect(page.getByTestId("shot-accept")).toContainText("Parade, Wurf von #14 Kurt Beispiel (TV Testdorf)");
  // one count: the report's moment first, the other open ones after it
  await expect(page.getByTestId("shot-candidate-focus")).toContainText("1 von 1 mit Spielbericht · 2 weitere offen");
  // no throw-off yet: the times are the report's, one click leads to the throw-off step
  await expect(page.getByTestId("shot-candidates-kickoff")).toContainText("Der Anwurf fehlt noch");
  await expectAccessible(page);

  // Enter on the moment takes the report's entry (player and outcome pinned to the video)
  const rows = panel.getByTestId("shot-candidate-row");
  await expect(rows).toHaveCount(1);
  await rows.first().focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("shot-candidates-said")).toContainText("1. HZ 12:45: Parade, Wurf von #14 Kurt Beispiel (TV Testdorf) aus dem Spielbericht.");
  expect(reviews.at(-1)).toEqual({ status: "confirmed" });

  // the report's moments are done: the open ones follow, and the video goes to the next one
  // (paused at its lead-in: 12 s minus 6 s); a team first, then the outcome
  await expect(rows).toHaveCount(2);
  const video = page.getByTestId("video");
  await expect.poll(() => video.evaluate((v: HTMLVideoElement) => Math.round(v.currentTime))).toBe(6);
  await rows.first().focus();
  await page.keyboard.press("g");
  await expect(panel.getByText("Erst das Team wählen: 1 oder 2.")).toBeVisible();
  await page.keyboard.press("1");
  await page.keyboard.press("g");
  await expect(page.getByTestId("shot-candidates-said")).toContainText("1. HZ 12:52: Tor Herren 1.");
  expect(reviews.at(-1)).toEqual({ status: "confirmed", side: "own", outcome: "goal" });

  // the last one in the full-screen review: its clip plays by itself, the keys work at once;
  // X: not a shot; U takes it back
  await expect(rows).toHaveCount(1);
  await page.getByTestId("shots-review-open").click();
  const review = page.getByRole("dialog", { name: "Würfe prüfen" });
  await expect(review).toContainText("1 offen");
  await expect.poll(() => video.evaluate((v: HTMLVideoElement) => !v.paused)).toBe(true);
  await page.keyboard.press("x");
  await expect(page.getByTestId("shot-candidates-said")).toContainText("1. HZ 13:00: Kein Wurf.");
  await expect(review).toContainText("0 offen");
  await expect(panel.getByText("Alle Würfe sind geprüft.")).toBeVisible();
  await panel.getByRole("button", { name: "Rückgängig", exact: true }).click();
  await expect(rows).toHaveCount(1);
  expect(reviews.at(-1)).toEqual({ status: null });
  await expectAccessible(page);
  // Escape leaves the full screen
  await page.keyboard.press("Escape");
  await expect(review).toHaveCount(0);
});

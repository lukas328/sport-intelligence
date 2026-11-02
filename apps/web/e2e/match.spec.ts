import { statSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { MATCH_VIDEO } from "./global-setup";
import { expectAccessible, register, uniqueEmail } from "./helpers";

test.describe.configure({ mode: "serial" });

test("match: create, upload with pause and resume, processing, player, comment, clip, playlist, drawing", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(300_000);
  expect(statSync(MATCH_VIDEO).size).toBeGreaterThan(10 * 1024 * 1024);

  await register(page, uniqueEmail("m2"), "Coach Video");
  await page.getByLabel("Vereinsname").fill("HC Video");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();

  // create a match
  await page.getByRole("link", { name: "Spiele" }).first().click();
  await expect(page.getByText("Noch keine Spiele.")).toBeVisible();
  await expectAccessible(page);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Testdorf");
  await page.getByLabel("Wettbewerb (optional)").fill("3. Liga");
  await page.getByRole("button", { name: "Spiel anlegen" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("TV Testdorf");
  await expectAccessible(page);

  // upload, pause after the first part, continue with the same file.
  // Parts 2 and 3 are held back on the first attempt so the pause happens mid-upload.
  let slow = true;
  await page.route(/partNumber=[23]/, async (route) => {
    if (slow) await new Promise((r) => setTimeout(r, 8000));
    await route.continue().catch(() => undefined);
  });
  const input = page.getByTestId("video-file");
  await input.setInputFiles(MATCH_VIDEO);
  const progress = page.getByTestId("upload-progress");
  await expect(progress).toContainText(/^[1-9]\d? % hochgeladen/, { timeout: 30_000 });
  await page.getByRole("button", { name: "Pausieren" }).click();
  await expect(page.getByText(/Pausiert/)).toBeVisible();
  slow = false;
  await input.setInputFiles(MATCH_VIDEO);
  // resumed: progress starts above zero because part 1 is already stored
  await expect(progress).toContainText(/^[1-9]\d* % hochgeladen/);
  await expect(page.getByText("Upload fertig. Die Verarbeitung startet.")).toBeVisible({ timeout: 60_000 });

  // processing runs in the worker; progress arrives via SSE
  await expect(page.getByTestId("player")).toBeVisible({ timeout: 180_000 });
  await expect(page.getByText("Videoqualität:")).toBeVisible();

  // play: the HLS stream loads and time advances
  const video = page.getByTestId("video");
  await page.getByRole("button", { name: "Abspielen" }).click();
  await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => v.currentTime), { timeout: 20_000 }).toBeGreaterThan(1);
  await page.getByRole("button", { name: "Pause" }).click();

  // keyboard: frame step and 5 s jumps
  await page.getByTestId("player").focus();
  const t0 = await video.evaluate((v: HTMLVideoElement) => v.currentTime);
  await page.keyboard.press("ArrowRight");
  await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(t0 + 4);

  // comment at the current time
  await page.getByPlaceholder(/Kommentar bei/).fill("Rückzug zu langsam");
  await page.getByRole("button", { name: "Kommentieren" }).click();
  await expect(page.getByTestId("comments")).toContainText("Rückzug zu langsam");

  // clip with I and O keys
  await page.getByRole("tab", { name: "Clips" }).click();
  await page.getByTestId("player").focus();
  await video.evaluate((v: HTMLVideoElement) => (v.currentTime = 2));
  await page.keyboard.press("i");
  await video.evaluate((v: HTMLVideoElement) => (v.currentTime = 6));
  await page.keyboard.press("o");
  await page.getByLabel("Titel").fill("Gegenstoss");
  await page.getByRole("button", { name: "Clip speichern" }).click();
  await expect(page.getByTestId("clips")).toContainText("Gegenstoss");

  // drawing
  await page.getByRole("tab", { name: "Zeichnungen" }).click();
  await page.getByRole("button", { name: "Zeichnen (D)" }).click();
  const layer = page.getByTestId("draw-layer");
  const box = (await layer.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.3);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.5, { steps: 5 });
  await page.mouse.up();
  await page.getByRole("button", { name: "Zeichnung speichern" }).click();
  await expect(page.getByText("Zeichnung gespeichert.")).toBeVisible();
  await expectAccessible(page);
});

test("playlist: create and share with players", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(300_000);
  await register(page, uniqueEmail("pl"), "Coach Playlist");
  await page.getByLabel("Vereinsname").fill("HC Playlist");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("U19");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.getByRole("link", { name: "Playlists" }).click();
  await page.getByLabel("Name", { exact: true }).fill("Abwehr Training");
  await page.getByRole("button", { name: "Erstellen" }).click();
  await expect(page.getByRole("heading", { name: "Abwehr Training" })).toBeVisible();
  await expect(page.getByText(/Diese Playlist hat noch keine Clips/)).toBeVisible();
  await page.getByRole("button", { name: "Mit Spielern teilen" }).click();
  await expect(page.getByText("Für Spieler sichtbar")).toBeVisible();
  await expectAccessible(page);
});

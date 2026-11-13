import { statSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { MATCH_VIDEO } from "./global-setup";
import { expectAccessible, follow, openAnalysis, openLibrary, register, uniqueEmail } from "./helpers";

test.describe.configure({ mode: "serial" });

test("match: create, upload with pause and resume, processing, player, comment, clip, playlist, drawing", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(300_000);
  expect(statSync(MATCH_VIDEO).size).toBeGreaterThan(10 * 1024 * 1024);

  await register(page, uniqueEmail("m2"), "Coach Video");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Video");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();

  // create a match
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);
  await expect(page.getByText("Noch keine Spiele.")).toBeVisible();
  await expectAccessible(page);
  await page.getByLabel("Gegner", { exact: true }).fill("TV Testdorf");
  // the rest of the match details sits behind «Mehr» (UX test H07)
  await page.getByText("Mehr: Wettbewerb, Halle, Spieldauer, Trikots").click();
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
  await expect(page.getByText("Fertig hochgeladen.")).toBeVisible({ timeout: 60_000 });

  // processing runs in the worker; progress arrives via SSE
  await expect(page.getByTestId("player").filter({ visible: true })).toBeVisible({ timeout: 180_000 });
  // stages 2 to 5 run in the GPU worker (CPU locally): calibration, detection, tracking, teams;
  // the court is the first work step beside the player
  // the setup by hand sits behind one toggle; its questions are asked in Prüfen (UX test B10)
  // a freshly analysed video without goals: the plain video and the way on, never the old
  // capture tools (UX test N04)
  await expect(page.getByTestId("plain-stage")).toBeVisible();
  for (const old of ["Ereignis erfassen", "Tastenkürzel", "Abwehrsysteme"]) await expect(page.getByText(old).filter({ visible: true })).toHaveCount(0);
  await page.getByTestId("open-bench").click();
  await page.getByTestId("setup-toggle").click();
  await page.getByTestId("step-court").click();
  await expect(page.getByText("Videoqualität:")).toBeVisible();
  await expect(page.getByTestId("mini-court")).toBeVisible({ timeout: 180_000 });
  await expect(page.getByTestId("analysis-panel")).toContainText("Personen verfolgt");
  await expect(page.getByTestId("analysis-panel")).toContainText("Kalibrierung: automatisch");
  await page.getByRole("tab", { name: "Abwehrsysteme", exact: true }).click();
  await expect(page.getByTestId("formations")).toContainText("Abwehrsysteme");

  // play: the HLS stream loads and time advances
  const video = page.getByTestId("video");
  await page.getByTestId("player").filter({ visible: true }).getByRole("button", { name: "Abspielen" }).click();
  await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => v.currentTime), { timeout: 20_000 }).toBeGreaterThan(1);
  await page.getByTestId("player").filter({ visible: true }).getByRole("button", { name: "Pause" }).click();

  // keyboard: frame step and 5 s jumps
  await page.getByTestId("player").filter({ visible: true }).focus();
  const t0 = await video.evaluate((v: HTMLVideoElement) => v.currentTime);
  await page.keyboard.press("ArrowRight");
  await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(t0 + 4);

  // comment at the current time (notes beside the player)
  await page.getByRole("tab", { name: "Kommentare", exact: true }).click();
  await page.getByPlaceholder(/Kommentar bei/).fill("Rückzug zu langsam");
  await page.getByRole("button", { name: "Kommentieren" }).click();
  await expect(page.getByTestId("comments")).toContainText("Rückzug zu langsam");

  // clip with I and O keys
  await page.getByRole("tab", { name: "Szenen", exact: true }).click();
  const seekTo = async (s: number) => {
    await video.evaluate((v: HTMLVideoElement, t: number) => (v.currentTime = t), s);
    await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => Math.round(v.currentTime))).toBe(s);
  };
  // the clip form (the event list may hold buttons with the same time)
  const clipForm = page.getByRole("form", { name: "Szene speichern" });
  await seekTo(2);
  await clipForm.getByRole("button", { name: "Start setzen (I)" }).click();
  await expect(clipForm.getByRole("button", { name: "0:02" })).toBeVisible();
  await seekTo(6);
  await page.getByTestId("player").filter({ visible: true }).focus();
  await page.keyboard.press("o"); // keyboard shortcut for the end mark
  await expect(clipForm.getByRole("button", { name: "0:06" })).toBeVisible();
  await page.getByLabel("Titel").fill("Gegenstoss");
  await page.getByRole("button", { name: "Szene speichern" }).click();
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

  // event tagging: kickoff at 0:00, a goal by hotkey at the current video time
  await seekTo(0);
  // the throw-off is its own work step; events are tagged beside the video
  await page.getByTestId("step-kickoff").click();
  await page.getByTestId("kickoff-1").click();
  await expect(page.getByText(/Anwurf 1. Halbzeit bei 0:00/).first()).toBeVisible();
  await page.getByRole("tab", { name: "Ereignisse" }).click();
  await seekTo(8);
  await page.getByRole("tab", { name: "Ereignisse" }).focus();
  await page.keyboard.press("g");
  await expect(page.getByText(/Erfasst: Tor bei 0:08/)).toBeVisible();
  await page.getByRole("button", { name: "Fehlwurf" }).click();
  await expect(page.getByText(/Erfasst: Fehlwurf/)).toBeVisible();
  await expectAccessible(page);

  // the overview counts it, the number opens the event, the event jumps into the video
  await openAnalysis(page, "Übersicht");
  const table = page.getByTestId("comparison");
  await expect(table.getByRole("row", { name: /^Tore(?! pro)/ })).toContainText("1");
  await expect(table.getByRole("row", { name: /^Würfe/ })).toContainText("2");
  await table.getByRole("button", { name: "Tore Herren 1" }).click();
  const list = page.getByTestId("event-list");
  await expect(list).toContainText("1. HZ 0:08");
  await list.getByRole("button", { name: /Abspielen/ }).click();
  await expect(page.getByTestId("player").filter({ visible: true })).toBeVisible();
  await expect.poll(async () => video.evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(3.5);

  // tracks can be assigned to players; physical load per track with heatmap
  await page.getByTestId("step-players").click();
  await expect(page.getByTestId("identity-panel")).toBeVisible();
  await openAnalysis(page, "Laufleistung");
  await expect(page.getByTestId("physical-table")).toContainText("km");
  await page.getByRole("button", { name: /Aufenthaltsorte zeigen/ }).nth(1).click();
  await expect(page.getByTestId("court-heatmap")).toBeVisible();
  await expectAccessible(page);

  // the current moment of the video as a play on the tactics board
  await page.getByRole("tab", { name: "Video", exact: true }).click();
  await page.getByRole("button", { name: "Als Spielzug übernehmen" }).click();
  await expect(page.getByTestId("tactics-board")).toBeVisible();
  expect(await page.getByTestId("tactics-board").locator("[data-testid^=token-]").count()).toBeGreaterThan(4);
  await page.getByLabel("Name").fill("Szene aus Video");
  await page.getByRole("button", { name: "Spielzug speichern" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Szene aus Video" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Szene im Video öffnen" })).toBeVisible();
});

test("playlist: create and share with players", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  test.setTimeout(300_000);
  await register(page, uniqueEmail("pl"), "Coach Playlist");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Playlist");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("U19");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await openLibrary(page, "Sammlungen");
  await page.getByLabel("Name", { exact: true }).fill("Abwehr Training");
  await page.getByRole("button", { name: "Neue Sammlung" }).click();
  await expect(page.getByRole("heading", { name: "Abwehr Training" })).toBeVisible();
  await expect(page.getByText(/Diese Sammlung hat noch keine Szenen/)).toBeVisible();
  await page.getByRole("button", { name: "Im Team teilen", exact: true }).click();
  await expect(page.getByText("Für Spieler sichtbar")).toBeVisible();
  await expectAccessible(page);
});

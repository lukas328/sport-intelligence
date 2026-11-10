import { expect, test } from "@playwright/test";
import { expectAccessible, register, uniqueEmail } from "./helpers";

// M11: courtside marks with device time (5.3), profile page (5.8), paper photo page (5.9)
test("coach marks during a match, opens the profile and paper pages", async ({ page }, info) => {
  test.skip(info.project.name !== "chromium", "full flow runs once");
  await register(page, uniqueEmail("coach-m11"), "Coach Elf");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Elf");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 3");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;

  const match = await (
    await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/matches`, {
      headers: { "x-csrf-token": (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value },
      data: { opponent_name: "TV Markierung", kickoff_at: new Date().toISOString() },
    })
  ).json();

  // big buttons, marks go out right away when online
  await page.goto(`/app/${orgId}/matches/${match.id}/marks`);
  // the buttons carry the team names; a status line counts and names the last mark
  await page.getByRole("button", { name: "Tor Herren 3" }).click();
  await page.getByRole("button", { name: "Gute Aktion" }).click();
  await expect(page.getByText(/2 Markierungen · zuletzt Gute Aktion/)).toBeVisible();
  await expect(page.getByText("Alles hochgeladen")).toBeVisible({ timeout: 15_000 });
  await expectAccessible(page);
  await page.goto(`/app/${orgId}/matches/${match.id}`);
  await page.getByRole("tab", { name: "Spiel", exact: true }).click();
  await page.getByTestId("marks-panel").getByText(/Markiert während des Spiels \(2\)/).click();
  await expect(page.getByTestId("marks-panel")).toContainText("noch nicht mit dem Video abgeglichen");

  // the coach has no player profile: "Ich" (the old /profile redirects there) leaves it out
  await page.goto(`/app/${orgId}/profile`);
  await expect(page).toHaveURL(/\/me$/);
  await expect(page.getByRole("heading", { name: "Öffentliches Profil" })).toHaveCount(0);
  await expectAccessible(page);
  await page.goto("/p/nobody-123456");
  await expect(page.getByText("Dieses Profil ist nicht öffentlich.")).toBeVisible();

  // paper photos (old /paper opens the dialog "Spielbericht hinzufügen"): without a model key
  // the upload says so honestly
  await page.goto(`/app/${orgId}/teams/${teamId}/paper`);
  await expect(page.getByTestId("report-dialog")).toBeVisible();
  await page.getByLabel("Foto").setInputFiles({ name: "bogen.jpg", mimeType: "image/jpeg", buffer: Buffer.from([0xff, 0xd8, 0xff, 0x00]) });
  await page.getByRole("button", { name: "Auslesen" }).click();
  await expect(page.getByText("Das Auslesen von Fotos ist in dieser Installation nicht eingerichtet.")).toBeVisible();
});

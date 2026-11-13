import { expect, test } from "@playwright/test";
import { expectAccessible, register, uniqueEmail } from "./helpers";

// UX test B04, B05, B17: a collection the coach trims, shares in one step and shows full screen
test("collection: note, order, remove, rename, share with a lasting link, revoke, big screen", async ({ page, context }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("coll"), "Coach Sammlung");
  await page.getByTestId("manual-club").click();
  await page.getByLabel("Vereinsname").fill("HC Sammlung");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await page.getByLabel("Teamname").fill("Herren 2");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  const created = await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/collections`, {
    headers: { "x-csrf-token": csrf },
    data: { title: "Rückzug", items: [{ kind: "note", text: "Erst schauen" }, { kind: "note", text: "Dann laufen" }] },
  });
  const { id } = await created.json();
  await page.goto(`/app/${orgId}/collections/${id}`);
  const items = page.getByTestId("collection-item");
  await expect(items).toHaveCount(2);

  // a note at the end
  await page.getByTestId("add-note").click();
  await page.getByLabel("Notiz").fill("Nur zwei laufen zurück!");
  await page.getByRole("button", { name: "Notiz speichern" }).click();
  await expect(items).toHaveCount(3);
  await expect(items.nth(2)).toContainText("Nur zwei laufen zurück!");

  // the last one up, the first one away; saved at once
  await items.nth(2).getByRole("button", { name: "Nach oben" }).click();
  await expect(items.nth(1)).toContainText("Nur zwei laufen zurück!");
  // removing can be taken back for a few seconds (UX test N30)
  await items.nth(0).getByTestId("item-remove").click();
  await expect(items).toHaveCount(2);
  await page.getByTestId("undo-remove").getByRole("button", { name: "Rückgängig" }).click();
  await expect(items).toHaveCount(3);
  await expect(items.nth(0)).toContainText("Erst schauen");
  await items.nth(0).getByTestId("item-remove").click();
  await expect(items).toHaveCount(2);
  await expect(page.getByTestId("collection-editor")).toHaveAttribute("aria-busy", "false");
  await page.reload();
  await expect(items).toHaveCount(2);
  await expect(items.nth(0)).toContainText("Nur zwei laufen zurück!");

  // a note right where it belongs, after the first entry (UX test N29)
  await items.nth(0).getByTestId("item-note-after").click();
  await page.getByLabel("Notiz").fill("Dazwischen");
  await page.getByRole("button", { name: "Notiz speichern" }).click();
  await expect(items).toHaveCount(3);
  await expect(items.nth(1)).toContainText("Dazwischen");

  // the title by a tap
  await page.getByTestId("collection-title").click();
  await page.getByLabel("Titel ändern").fill("Rückzug nach Ballverlust");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Rückzug nach Ballverlust");

  // share in one step: the link stays visible and copyable after a reload, then it is revoked
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.getByTestId("share-create").click();
  await expect(page.getByTestId("share-url")).toHaveValue(/\/s\/[\w-]{20,}/);
  const url = await page.getByTestId("share-url").inputValue();
  await page.reload();
  await expect(page.getByTestId("share-url")).toHaveValue(url);
  await expect(page.getByTestId("share-views")).toHaveText("0");
  await expectAccessible(page);
  const anon = await (await page.context().browser()!.newContext()).newPage();
  await anon.goto(url);
  await expect(anon.getByRole("heading", { level: 1 })).toContainText("Rückzug nach Ballverlust");
  await expect(anon.getByText("Anmelden")).toHaveCount(0);
  await page.getByTestId("share-revoke").click();
  await expect(page.getByTestId("share-create")).toBeVisible();
  await anon.reload();
  await expect(anon.getByText("Dieser Link ist abgelaufen oder wurde zurückgezogen.")).toBeVisible();

  // «Am Bildschirm zeigen» is a real view of its own
  await page.getByTestId("present").click();
  await expect(page.getByTestId("present-view")).toBeVisible();
  await expect(page.getByTestId("present-view")).toContainText("Nur zwei laufen zurück!");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("present-view")).toContainText("2 von 3");
});

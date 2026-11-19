import { expect, test } from "@playwright/test";
import { clubByHand, expectAccessible, register, uniqueEmail } from "./helpers";

const doc = {
  formatVersion: 1,
  court: "half",
  frames: [
    {
      tokens: [
        { id: "a", side: "own", label: "RM", x: 28, y: 10 },
        { id: "b", side: "own", label: "RL", x: 29, y: 4.5 },
        { id: "c", side: "opp", label: "3", x: 34, y: 9 },
      ],
      ball: { x: 28.5, y: 10 },
      arrows: [{ kind: "pass", points: [[28, 10], [29, 4.5]] }],
      note: "",
      duration_ms: 1500,
    },
  ],
};

// K20: one share action, a prepared chat text, WhatsApp, a link preview for every chat, and a
// public page made for the phone (390 px) without app frame or login
test("share: dialog with chat text and WhatsApp, link preview tags, public page at 390 px", async ({ page, context, browser }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("share"), "Coach Chat");
  await clubByHand(page, "HC Teilen");
  await page.getByLabel("Teamname").fill("Herren 1");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  const play = await (await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/plays`, { headers: { "x-csrf-token": csrf }, data: { name: "Kreuzen Rückraum", category: "attack", doc } })).json();

  // the dialog: expiry with a default, then the link, the chat text and the ways into the chat
  await page.goto(`/app/${orgId}/plays/${play.id}`);
  await page.getByRole("button", { name: "Teilen", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "Spielzug teilen" })).toBeVisible();
  await expect(dialog.getByRole("radio", { name: "30 Tage" })).toBeChecked();
  await dialog.getByText("7 Tage").click();
  await dialog.getByRole("button", { name: "Link erstellen" }).click();
  const url = await dialog.getByTestId("share-url").inputValue();
  expect(url).toMatch(/\/s\/[\w-]{20,}$/);
  await expect(dialog.getByTestId("share-text")).toHaveValue("📋 Spielzug «Kreuzen Rückraum»: bitte vor dem Training anschauen.");
  const wa = await dialog.getByTestId("share-whatsapp").getAttribute("href");
  expect(wa).toMatch(/^https:\/\/wa\.me\/\?text=/);
  expect(decodeURIComponent(wa!.split("text=")[1]!)).toBe(`📋 Spielzug «Kreuzen Rückraum»: bitte vor dem Training anschauen.\n${url}`);
  await expect(dialog.getByTestId("share-status")).toContainText("noch nicht geöffnet");
  await expectAccessible(page);
  await page.keyboard.press("Escape");
  // opened again: the same link, no second one
  await page.getByRole("button", { name: "Teilen", exact: true }).click();
  await expect(page.getByRole("dialog").getByTestId("share-url")).toHaveValue(url);
  await expect(page.getByRole("dialog").getByText("Schon geteilt")).toBeVisible();
  await page.keyboard.press("Escape");

  // what the chats read: tags in the server <head>, an absolute 1200 x 630 picture
  const html = await (await page.request.get(url, { headers: { "user-agent": "WhatsApp/2.24.6.77 A" } })).text();
  const head = html.split("</head>")[0]!;
  expect(head).toContain('<meta property="og:title" content="Spielzug: Kreuzen Rückraum"/>');
  expect(head).toMatch(/<meta property="og:image" content="https?:\/\/[^"]+\/s\/[\w-]+\/og\?v=\d+"\/>/);
  expect(head).toContain('<meta property="og:image:width" content="1200"/>');
  expect(head).toContain('<meta name="twitter:card" content="summary_large_image"/>');
  expect(head).toContain('content="noindex, nofollow"');
  const image = await page.request.get(`${new URL(url).pathname}/og?v=2`);
  expect(image.headers()["content-type"]).toContain("image/png");
  expect((await image.body()).length).toBeLessThan(300 * 1024);

  // the public page on a phone: no app frame, no login, no sideways scrolling, the footer
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: "de-CH" });
  const guest = await phone.newPage();
  await guest.goto(url);
  await expect(guest.getByRole("heading", { level: 1, name: "Kreuzen Rückraum" })).toBeVisible();
  await expect(guest.getByText("Spielzug · 1 Phase")).toBeVisible();
  await expect(guest.getByText("Anmelden")).toHaveCount(0);
  await expect(guest.getByRole("link", { name: "Gemacht mit Handball Intelligence" })).toHaveAttribute("href", /\/de\/\?src=shared$/);
  expect(await guest.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  await expectAccessible(guest);
  await phone.close();

  // the preview does not count, the opening does
  const links = await (await page.request.get(`/v1/orgs/${orgId}/teams/${teamId}/share-links`)).json();
  expect(links[0].views).toBe(1);

  // «Link sperren»: the page says so
  await page.getByRole("button", { name: "Teilen", exact: true }).click();
  await page.getByRole("dialog").getByTestId("share-revoke-link").click();
  await expect(page.getByRole("dialog").getByText("Link gesperrt")).toBeVisible();
  const gone = await (await browser.newContext()).newPage();
  await gone.goto(url);
  await expect(gone.getByText("Dieser Link ist abgelaufen oder wurde zurückgezogen.")).toBeVisible();
});

// K18, K20: a youth team shares plays only; the dialog explains it instead of failing
test("share: a youth team gets the reason, not an error", async ({ page, context }, info) => {
  test.skip(info.project.name !== "chromium", "runs once");
  await register(page, uniqueEmail("share-youth"), "Coach Junioren");
  await clubByHand(page, "HC Junioren");
  await page.getByLabel("Teamname").fill("U13");
  await page.getByRole("button", { name: "Zum Team" }).click();
  await page.waitForURL(/\/teams\/[^/]+/);
  const [, orgId, teamId] = page.url().match(/\/app\/([^/]+)\/teams\/([^/?#]+)/)!;
  const csrf = (await context.cookies()).find((c) => c.name === "hb_csrf")!.value;
  await page.request.patch(`/v1/orgs/${orgId}/teams/${teamId}`, { headers: { "x-csrf-token": csrf }, data: { is_youth: true } });
  const coll = await (await page.request.post(`/v1/orgs/${orgId}/teams/${teamId}/collections`, { headers: { "x-csrf-token": csrf }, data: { title: "Abwehr", items: [{ kind: "note", text: "Schauen" }] } })).json();
  await page.goto(`/app/${orgId}/collections/${coll.id}`);
  await expect(page.getByTestId("share-blocked")).toContainText("Junioren-Teams teilen öffentlich nur Spielzüge");
  await expect(page.getByTestId("share-create")).toHaveCount(0);
});

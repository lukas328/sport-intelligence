import AxeBuilder from "@axe-core/playwright";
import { expect, type Locator, type Page } from "@playwright/test";

export const MAILPIT = process.env.E2E_MAILPIT_URL ?? "http://localhost:8025";

export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@hc-e2e.ch`;
}

/** Waits for the latest e-mail to `to` and returns the first link in it that contains `path`. */
export async function linkFromMail(page: Page, to: string, path: string): Promise<string> {
  // generous: during the full run the video analysis keeps the CPU busy
  for (let i = 0; i < 120; i++) {
    const res = await page.request.get(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:"${to}"`)}`);
    const { messages } = (await res.json()) as { messages: { ID: string }[] };
    if (messages.length > 0) {
      const msg = (await (await page.request.get(`${MAILPIT}/api/v1/message/${messages[0]!.ID}`)).json()) as {
        Text: string;
      };
      const match = msg.Text.match(new RegExp(`https?://\\S*${path}\\S*`));
      if (match) return match[0];
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`no mail with ${path} for ${to}`);
}

export async function expectAccessible(page: Page) {
  // metadata (the <title>) is streamed after client-side navigations
  await expect.poll(() => page.title()).not.toBe("");
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(
    result.violations.flatMap((v) => v.nodes.map((n) => `${v.id}: ${n.target.join(" ")} ${n.failureSummary ?? ""}`)),
  ).toEqual([]);
}

export async function register(page: Page, email: string, name = "Test Trainerin") {
  await page.goto("/register");
  await page.getByLabel("Vor- und Nachname").fill(name);
  await page.getByLabel("E-Mail").fill(email);
  await page.getByLabel("Passwort").fill("correct-horse-1");
  await page.getByLabel(/Nutzungsbedingungen/).check();
  await page.getByRole("button", { name: "Konto erstellen" }).click();
  // password hashing is deliberately slow; wait until the app has moved on
  await page.waitForURL((url) => !url.pathname.startsWith("/register"), { timeout: 30_000 });
}

/** Team area: "Team" in the main navigation, then a section (Kader, Termine). */
export async function openTeam(page: Page, section?: "Kader" | "Termine") {
  await follow(page, page.getByRole("link", { name: "Team", exact: true }), /\/teams\/[^/]+$/);
  if (!section || section === "Kader") return;
  await follow(page, page.getByRole("link", { name: section, exact: true }), /\/schedule$/);
}

/** Spiele in the main navigation (the start for staff). Saison is a destination of its own;
 * "Bibliothek" is the collections tab of Szenen (SPEC section 6). */
export async function openMatches(page: Page, section?: "Spielplan" | "Saison" | "Bibliothek") {
  if (section === "Saison") return follow(page, page.getByRole("link", { name: "Saison", exact: true }).first(), /\/season$/);
  if (section === "Bibliothek") return openScenes(page, "Sammlungen");
  await follow(page, page.getByRole("link", { name: "Spiele", exact: true }).first(), /\/matches$/);
}

/** Szenen in the main navigation, then a tab (Szenen, Sammlungen, Spielzüge, Tabelle). */
export async function openScenes(page: Page, tab?: "Szenen" | "Sammlungen" | "Spielzüge" | "Tabelle") {
  await follow(page, page.getByRole("link", { name: "Szenen", exact: true }).first(), /\/scenes$/);
  if (!tab || tab === "Szenen") return;
  const path = { Sammlungen: "library", Spielzüge: "plays", Tabelle: "matrix" }[tab];
  await follow(page, page.getByRole("link", { name: tab, exact: true }).first(), new RegExp(`/${path}$`));
}

/** Library entry (Playlists, Präsentationen) under Sammlungen; the scene search is Szenen itself. */
export async function openLibrary(page: Page, entry: "Playlists" | "Präsentationen" | "Szenensuche") {
  if (entry === "Szenensuche") return openScenes(page);
  await openScenes(page, "Sammlungen");
  const path = { Playlists: "playlists", Präsentationen: "presentations" }[entry];
  await follow(page, page.getByRole("link", { name: new RegExp(`^${entry}`) }), new RegExp(`/${path}$`));
}

/** Plays: a tab of Szenen. */
export async function openPlays(page: Page) {
  await openScenes(page, "Spielzüge");
}

/** The training plan is out of the main navigation (SPEC section 1, "Next"); its route stays. */
export async function openTraining(page: Page) {
  const team = /\/app\/[^/]+\/teams\/[0-9a-f-]{36}/.exec(page.url())?.[0];
  if (!team) await follow(page, page.getByRole("link", { name: "Team", exact: true }).first(), /\/teams\/[^/]+$/);
  const base = /\/app\/[^/]+\/teams\/[0-9a-f-]{36}/.exec(page.url())![0];
  await page.goto(`${base}/training`);
  await page.waitForURL(/\/training$/);
}

/** Match page: analysis view and one of its sections. */
export async function openAnalysis(page: Page, section: "Übersicht" | "Würfe" | "Torhüter" | "Laufleistung" | "Matchbericht") {
  await page.getByRole("tab", { name: "Analyse", exact: true }).click();
  await page.getByRole("tab", { name: section, exact: true }).click();
}

/** Match page: an entry of the "Mehr" menu. */
export async function matchMenu(page: Page) {
  await page.getByTestId("match-menu").click();
}

/**
 * Clicks a link and waits for the URL. Under the full parallel run a click can land while the
 * previous route is still streaming in; one retry keeps the flows stable.
 */
export async function follow(page: Page, link: Locator, url: RegExp) {
  await link.click();
  try {
    await page.waitForURL(url, { timeout: 10_000 });
  } catch {
    await link.click();
    await page.waitForURL(url);
  }
}

// Captures every screen of the app for docs/screens (not a test; run with screens.config.ts against
// the local stack with the demo club from scripts/seed.py, then: python3 docs/screens/build.py).
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import * as fx from "../e2e/fixtures/official";
import { shotList } from "../e2e/fixtures/shots";
import { linkFromMail, register, uniqueEmail } from "../e2e/helpers";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../docs/screens/png");
const counters: Record<string, number> = {};
const json = (body: unknown, status = 200) => ({ status, contentType: "application/json", body: JSON.stringify(body) });

async function snap(page: Page, group: string, name: string, prep?: () => Promise<void>) {
  mkdirSync(`${ROOT}/${group}`, { recursive: true });
  const nr = String((counters[group] = (counters[group] ?? 0) + 1)).padStart(2, "0");
  for (const [mode, w, h] of [["desktop", 1440, 900], ["phone", 390, 844]] as const) {
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(900);
    if (prep) await prep().catch(() => undefined);
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${ROOT}/${group}/${nr}-${name}-${mode}.png`, fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}
async function go(page: Page, url: string) {
  await page.goto(url);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(1500);
}
const tryClick = async (page: Page, testId: string) => {
  const el = page.getByTestId(testId).first();
  if (await el.isVisible().catch(() => false)) await el.click();
};

test.use({ deviceScaleFactor: 1, actionTimeout: 15_000, navigationTimeout: 45_000 });

test("screens", async ({ page, browser }, info) => {
  test.skip(info.project.name !== "chromium");
  test.setTimeout(1_800_000);

  // ---------------- 1 Einstieg ----------------
  const E = "1-einstieg";
  await go(page, "/login");
  await snap(page, E, "anmelden");
  await go(page, "/register");
  await snap(page, E, "registrieren");
  await go(page, "/auth/forgot");
  await snap(page, E, "passwort-vergessen");
  await page.route("**/v1/official/teams?*", (r) => r.fulfill(json(fx.searchHits)));
  await register(page, uniqueEmail("atlas"), "Sandra Trainerin");
  await snap(page, E, "onboarding-mannschaft-suchen");
  await page.getByLabel("Team oder Verein").fill("Seeblick");
  await expect(page.getByTestId("official-team").first()).toBeVisible();
  await snap(page, E, "onboarding-suchergebnis");
  // step 2 «Das seid ihr, oder?» after taking a team over (answers recorded, invented names)
  {
    const p2 = await page.context().newPage();
    const claimed = `**/v1/orgs/${fx.CLAIMED_ORG}/teams/${fx.CLAIMED_TEAM}`;
    await p2.route("**/v1/official/teams?*", (r) => r.fulfill(json(fx.searchHits)));
    await p2.route("**/v1/official/teams/*/claim", (r) => r.fulfill(json(fx.claimed(fx.CLAIMED_ORG, fx.CLAIMED_TEAM), 201)));
    await p2.route(`${claimed}/official`, (r) => r.fulfill(json(fx.link)));
    await p2.route(`${claimed}/official/suggestions*`, (r) => r.fulfill(json(fx.suggestions)));
    await p2.route(`${claimed}/matches`, (r) =>
      r.fulfill(json([{ id: "00000000-0000-4000-8000-00000000a001", team_id: fx.CLAIMED_TEAM, kind: "match", kickoff_at: "2026-11-07T17:00:00Z", opponent_name: "TSV Thalwil", is_home: true, score_own: 26, score_opponent: 18, status: "finished", has_video: false, is_demo: false, competition: null }])),
    );
    await go(p2, "/onboarding");
    await p2.getByLabel("Team oder Verein").fill("Seeblick");
    await p2.getByTestId("official-team").filter({ hasText: "HC Seeblick Herren 1" }).getByTestId("claim").click();
    await expect(p2.getByTestId("claim-done")).toContainText("Timo Brunner");
    await snap(p2, E, "onboarding-das-seid-ihr");
    await p2.close();
  }
  await page.getByTestId("manual-club").click();
  await snap(page, E, "onboarding-verein-von-hand");
  await page.getByLabel("Vereinsname").fill("HC Seeblick");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await expect(page.getByLabel("Teamname")).toBeVisible();
  await snap(page, E, "onboarding-team");
  await page.getByLabel("Teamname").fill("Damen 1");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await expect(page.getByRole("form", { name: "Spieler hinzufügen" })).toBeVisible();
  await snap(page, E, "onboarding-kader");
  await page.getByRole("button", { name: "Weiter", exact: true }).click();
  await snap(page, E, "onboarding-einladen");
  await page.context().clearCookies();
  await page.unroute("**/v1/official/teams?*");

  // ---------------- 2 Trainer (demo club) ----------------
  const T = "2-trainer";
  await go(page, "/login");
  await page.getByLabel("E-Mail").fill("demo@handball-demo.ch");
  await page.getByLabel("Passwort").fill("demo-handball-2026");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.waitForURL(/\/app\/[^/]+/);
  const org = page.url().match(/\/app\/([^/?#]+)/)![1]!;
  const csrf = (await page.context().cookies()).find((c) => c.name === "hb_csrf")!.value;
  const h = { "x-csrf-token": csrf };
  const teams = (await (await page.request.get(`/v1/orgs/${org}/teams`)).json()) as { id: string; name: string }[];
  const team = teams[0]!;
  const tinfo = await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}`)).json();
  const season = tinfo.current_season;
  const base = `/app/${org}/teams/${team.id}`;
  const roster = (await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/seasons/${season.id}/roster`)).json()) as {
    player_id: string;
    first_name: string;
    last_name: string;
    has_account: boolean;
  }[];
  // realistic extras for this night's features (ignored when already there)
  const until = new Date(Date.now() + 9 * 86400_000).toISOString().slice(0, 10);
  await page.request.put(`/v1/orgs/${org}/teams/${team.id}/players/${roster[1]!.player_id}/status`, { headers: h, data: { kind: "injured", until, note: "Knöchel" } });
  await page.request.put(`/v1/orgs/${org}/teams/${team.id}/players/${roster[3]!.player_id}/status`, { headers: h, data: { kind: "absent" } });
  const slots = await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/seasons/${season.id}/training-slots`)).json();
  if (!slots.length) {
    await page.request.post(`/v1/orgs/${org}/teams/${team.id}/seasons/${season.id}/training-slots`, { headers: h, data: { weekday: 2, start_time: "19:00", duration_min: 90, location: "Halle Seefeld" } });
    await page.request.post(`/v1/orgs/${org}/teams/${team.id}/seasons/${season.id}/training-slots`, { headers: h, data: { weekday: 4, start_time: "18:30", duration_min: 90, location: "Halle Seefeld", title: "Abschluss" } });
    await page.request.post(`/v1/orgs/${org}/teams/${team.id}/seasons/${season.id}/training-slots/generate`, { headers: h, data: { skip_dates: [] } });
  }
  const drills = (await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/drills?lang=de-CH`)).json()) as { source: string }[];
  if (!drills.some((d) => d.source === "club"))
    await page.request.post(`/v1/orgs/${org}/teams/${team.id}/drills`, { headers: h, data: { name: "Kreuzen im Rückraum", minutes: 20, players: "6-12", level: "advanced", focus: ["back_court", "passing"], setup: "Zwei Rückraumspieler kreuzen, der Kreis sperrt.", coaching: "Tempo vor dem Kreuzen, Blick zum Tor.", shared: true } });
  const assignments = await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/assignments`)).json();
  if (!assignments.length) await page.request.post(`/v1/orgs/${org}/teams/${team.id}/assignments`, { headers: h, data: { kind: "drill", target_id: "wing-finishing", title: "Flügelwürfe unter Druck", recipients: "all" } }).catch(() => undefined);
  let playlists = await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/playlists`)).json();
  if (!playlists.length) {
    await page.request.post(`/v1/orgs/${org}/teams/${team.id}/playlists`, { headers: h, data: { title: "Abwehr 6:0" } });
    playlists = await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/playlists`)).json();
  }
  let pres = await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/presentations`)).json();
  if (!pres.length) {
    await page.request.post(`/v1/orgs/${org}/teams/${team.id}/presentations`, { headers: h, data: { title: "Gegner TV Testdorf" } });
    pres = await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/presentations`)).json();
  }
  const matches = (await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/matches`)).json()) as {
    id: string;
    has_video: boolean;
    score_own: number | null;
    opponent?: { id: string } | null;
    kickoff_at: string;
  }[];
  const withVideo = matches.find((m) => m.has_video) ?? matches[0]!;
  const upcoming = matches.find((m) => m.score_own == null && !m.has_video && Date.parse(m.kickoff_at) > Date.now()) ?? matches[0]!;
  const plays = await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/plays`)).json();

  // staff start on Spiele (SPEC section 6): /app/<org> redirects there
  await go(page, `/app/${org}`);
  await snap(page, T, "spiele");
  await go(page, `${base}/matches?upload=1`);
  await snap(page, T, "video-hochladen");
  await go(page, `${base}/matches?new=1`);
  await snap(page, T, "neues-spiel");
  await go(page, `/app/${org}/matches/${upcoming.id}`);
  await snap(page, T, "spiel-vor-dem-anpfiff", async () => {
    const d = page.getByTestId("match-attendance");
    if (await d.isVisible()) await d.locator("summary").click();
  });

  // the match workspace, step by step (shot moments from the recorded fixture)
  await page.route("**/v1/orgs/*/matches/*/shot-candidates", (r) => r.fulfill(json(shotList())));
  await go(page, `/app/${org}/matches/${withVideo.id}`);
  await expect(page.getByTestId("player")).toBeVisible({ timeout: 60_000 });
  // the tab Video: one stage (video or tactics camera), the workbench behind «Mehr»
  await snap(page, T, "spiel-video");
  await snap(page, T, "spiel-video-werkbank", () => tryClick(page, "bench-open"));
  if (await page.getByTestId("shots-review-open").isVisible().catch(() => false)) {
    await page.getByTestId("shots-review-open").click();
    await snap(page, T, "spiel-wuerfe-vollbild");
    await page.keyboard.press("Escape");
  }
  // one level of tabs: Spiel · Video · Zahlen
  await snap(page, T, "spiel-spiel", async () => {
    await page.getByRole("tab", { name: "Spiel", exact: true }).click();
  });
  await snap(page, T, "spiel-zahlen", async () => {
    await page.getByRole("tab", { name: "Zahlen", exact: true }).click();
  });
  await page.unroute("**/v1/orgs/*/matches/*/shot-candidates");
  // Prüfen: one question at a time
  await go(page, `/app/${org}/matches/${withVideo.id}/check`);
  await snap(page, T, "spiel-pruefen");
  await go(page, `/app/${org}/matches/${upcoming.id}/matchday`);
  await snap(page, T, "spieltag");
  await go(page, `/app/${org}/matches/${upcoming.id}/matchday?mode=marks`);
  await snap(page, T, "spieltag-markieren");
  await go(page, `/app/${org}/matches/${upcoming.id}/scouting`);
  await snap(page, T, "spiel-scouting");
  await go(page, `${base}/matches?report=1`);
  await snap(page, T, "spielbericht-hinzufuegen");
  const opponent = matches.find((m) => m.opponent?.id)?.opponent?.id;
  if (opponent) {
    await go(page, `/app/${org}/opponents/${opponent}`);
    await snap(page, T, "gegner-profil");
  }
  await go(page, `${base}/season`);
  await snap(page, T, "saison");
  await go(page, `${base}/matrix`);
  await snap(page, T, "statistik-matrix");
  await go(page, `${base}/assistant`);
  await snap(page, T, "assistent");
  await go(page, `${base}/scenes`);
  await snap(page, T, "szenen");
  await go(page, `${base}/collections`);
  await snap(page, T, "sammlungen");
  const collections = (await (await page.request.get(`/v1/orgs/${org}/teams/${team.id}/collections`)).json()) as { id: string }[];
  if (collections[0]) {
    await go(page, `${base}/collections/${collections[0].id}`);
    await snap(page, T, "sammlung");
  }
  await go(page, `${base}/playlists`);
  await snap(page, T, "playlists");
  if (playlists[0]) {
    await go(page, `/app/${org}/playlists/${playlists[0].id}`);
    await snap(page, T, "playlist");
  }
  await go(page, `${base}/presentations`);
  await snap(page, T, "praesentationen");
  if (pres[0]) {
    await go(page, `/app/${org}/presentations/${pres[0].id}`);
    await snap(page, T, "praesentation-bearbeiten");
  }
  await go(page, `${base}/training`);
  await snap(page, T, "training-plan");
  await go(page, `/app/${org}/drills`);
  await snap(page, T, "training-uebungen");
  await go(page, `${base}/plays`);
  await snap(page, T, "training-spielzuege");
  if (plays[0]) {
    await go(page, `/app/${org}/plays/${plays[0].id}`);
    await snap(page, T, "spielzug");
  }
  await go(page, `${base}/assignments`);
  await snap(page, T, "training-aufgaben");
  await go(page, base);
  await snap(page, T, "team-kader");
  await go(page, `${base}?edit=1`);
  await snap(page, T, "team-kader-bearbeiten", async () => {
    const d = page.getByTestId("consent-overview");
    if (await d.isVisible()) if (!(await d.evaluate((e) => (e as HTMLDetailsElement).open))) await d.locator("summary").click();
  });
  await go(page, `${base}/players/${roster[1]!.player_id}`);
  await snap(page, T, "team-saisonverlauf-spielerin");
  await go(page, `/app/${org}/schedule`);
  await snap(page, T, "team-termine");
  // official data: answers recorded with invented names (handball.ch is not reached)
  await page.route(`**/v1/orgs/${org}/teams/${team.id}/official`, (r) => r.fulfill(json(fx.link)));
  await page.route(`**/v1/orgs/${org}/teams/${team.id}/official/suggestions?*`, (r) => r.fulfill(json(fx.suggestions)));
  await go(page, `${base}/official`);
  await snap(page, T, "team-abgleich-handball-ch");
  const id = (n: number) => `00000000-0000-4000-8000-00000000${String(n).padStart(4, "0")}`;
  await page.route(`**/v1/orgs/${org}/teams/${team.id}/join-requests`, (r) =>
    r.fulfill(json([{ id: id(1), team_id: team.id, user_id: id(11), email: "lara.muster@example.ch", first_name: "Lara", last_name: "Muster", jersey_number: 11, role: "player", message: "Ich spiele seit August mit.", status: "pending", created_at: new Date().toISOString(), suggested: null, player_id: null }])),
  );
  await go(page, `${base}/join-requests`);
  await snap(page, T, "team-beitrittsanfragen");
  for (const [path, name] of [
    ["me", "ich-profil"],
    ["me/security", "ich-sicherheit"],
    ["me/data", "ich-daten"],
    ["club", "verein"],
    ["club/teams", "verein-teams"],
    ["club/billing", "verein-abo"],
  ] as const) {
    await go(page, `/app/${org}/${path}`);
    await snap(page, T, name);
  }
  await go(page, `${base}/matches`);
  await snap(page, T, "mitteilungen", async () => {
    await page.keyboard.press("Escape");
    await page.getByTestId("bell").filter({ visible: true }).first().click({ timeout: 5000 });
  });
  await page.keyboard.press("Escape");

  // ---------------- 3 Spielerin and 4 Eltern ----------------
  const free = roster.filter((r) => !r.has_account);
  const invite = async (role: "player" | "parent", child: { player_id: string; first_name: string; last_name: string }, name: string) => {
    const email = uniqueEmail(role);
    await page.request.post(`/v1/orgs/${org}/invitations`, { headers: h, data: { email, team_id: team.id, team_role: role, player_id: child.player_id } });
    const link = await linkFromMail(page, email, "/invite/");
    const ctx = await browser.newContext();
    const p = await ctx.newPage();
    await p.goto(link);
    await p.getByRole("link", { name: "Konto erstellen und annehmen" }).click();
    await p.getByLabel("Vor- und Nachname").fill(name);
    await p.getByLabel("Passwort").fill("correct-horse-1");
    await p.getByLabel(/Nutzungsbedingungen/).check();
    await p.getByRole("button", { name: "Konto erstellen" }).click();
    await p.waitForURL((url) => !url.pathname.startsWith("/register"), { timeout: 30_000 });
    return { ctx, p };
  };
  if (free[0]) {
    const S = "3-spielerin";
    const { ctx, p } = await invite("player", free[0], `${free[0].first_name} ${free[0].last_name}`);
    await go(p, `/app/${org}`);
    await snap(p, S, "uebersicht");
    await go(p, `/app/${org}/feed`);
    await snap(p, S, "meine-szenen");
    const feeds = await (await p.request.get(`/v1/orgs/${org}/me/feeds`)).json();
    if (feeds[0]) {
      await go(p, `/app/${org}/feed/${feeds[0].match_id}?player=${feeds[0].player_id}`);
      await snap(p, S, "szenen-eines-spiels");
    }
    await go(p, `/app/${org}/schedule`);
    await snap(p, S, "termine");
    await go(p, `/app/${org}/teams/${team.id}`);
    await snap(p, S, "team");
    await go(p, `/app/${org}/assignments`);
    await snap(p, S, "aufgaben");
    await go(p, `/app/${org}/matches/${withVideo.id}`);
    await snap(p, S, "spiel");
    await go(p, `/app/${org}/teams/${team.id}/players/${free[0].player_id}`);
    await snap(p, S, "mein-saisonverlauf");
    await go(p, `/app/${org}/me`);
    await snap(p, S, "ich");
    await go(p, `/app/${org}/consents`);
    await snap(p, S, "einwilligungen");
    await ctx.close();
  }
  if (free[1]) {
    const P = "4-eltern";
    const { ctx, p } = await invite("parent", free[1], "Eva Beispiel");
    await go(p, `/app/${org}`);
    await snap(p, P, "uebersicht");
    await go(p, `/app/${org}/schedule`);
    await snap(p, P, "termine");
    await go(p, `/app/${org}/consents`);
    await snap(p, P, "einwilligungen-fuer-das-kind");
    await go(p, `/app/${org}/feed`);
    await snap(p, P, "szenen-des-kindes");
    await ctx.close();
  }

  // ---------------- 5 Öffentlich ----------------
  const O = "5-oeffentlich";
  const anon = await browser.newContext();
  const a = await anon.newPage();
  await go(a, "/status");
  await snap(a, O, "systemstatus");
  await go(a, "/federation");
  await snap(a, O, "verband");
  await anon.close();
});

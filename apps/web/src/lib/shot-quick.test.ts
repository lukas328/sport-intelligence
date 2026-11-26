import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../messages/de-CH.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";
import { ShellContext, type ShellValue } from "@/components/shell/context";
import { ShotQuick } from "@/app/app/[orgId]/matches/[matchId]/check/shot-quick";
import type { CandidateList } from "./goal-candidates";
import { quickBody, quickQueue, quickWindow, startSide, type ShotCandidate } from "./shot-candidates";

// «Würfe schnell prüfen»: the shots the analysis found, the least sure first, a short clip each,
// four answers saved through the same review as the shot list. Invented clubs.
const cand = (id: string, goal_ms: number, score: number, extra: Partial<ShotCandidate> = {}): ShotCandidate =>
  ({
    id,
    kind: "shot",
    video_asset_id: "v1",
    t_ms: goal_ms + 1500,
    goal_ms,
    start_ms: goal_ms - 8000,
    end_ms: goal_ms + 4000,
    score,
    rate: 2,
    suggested_side: "own",
    status: "open",
    skipped: false,
    auto: false,
    side: null,
    outcome: null,
    event_id: null,
    period: 1,
    clock_s: goal_ms / 1000,
    known: null,
    suggestion: null,
    ...extra,
  }) as ShotCandidate;

const list = (candidates: ShotCandidate[]): CandidateList =>
  ({ candidates, rates: [2, 4, 6], default_rate: 4, counts: { total: candidates.length, open: candidates.length, open_by_rate: {}, confirmed: 0, rejected: 0, suggested: 0 } }) as unknown as CandidateList;

describe("quickQueue: what the quick review asks, in which order", () => {
  it("open shots at the default rate, not known already, the least sure first, then by time", () => {
    const l = list([
      cand("sure", 10_000, 0.9),
      cand("unsure", 50_000, 0.2),
      cand("unsure-early", 20_000, 0.2),
      cand("too-rare", 30_000, 0.1, { rate: 6 }),
      cand("known", 40_000, 0.1, { known: { source: "report" } as never }),
      cand("done", 60_000, 0.1, { status: "confirmed" }),
    ]);
    expect(quickQueue(l).map((c) => c.id)).toEqual(["unsure-early", "unsure", "sure"]);
  });
});

describe("the clip and the answers", () => {
  it("plays from 1.5 s before the shot to 2 s after (3.5 s, looped)", () => {
    expect(quickWindow({ goal_ms: 12_000 })).toEqual({ start_ms: 10_500, end_ms: 14_000 });
    expect(quickWindow({ goal_ms: 800 }).start_ms).toBe(0);
  });

  it("«Kein Wurf» rejects; an outcome needs a team; the report's entry is pinned when it says the same", () => {
    const c = cand("a", 10_000, 0.3);
    expect(quickBody(c, "own", "none")).toEqual({ status: "rejected" });
    expect(quickBody(c, "opponent", "save")).toEqual({ status: "confirmed", side: "opponent", outcome: "save" });
    expect(quickBody({ ...c, suggested_side: null }, null, "goal")).toBeNull();
    const withReport = cand("b", 10_000, 0.3, { suggestion: { side: "own", outcome: "goal" } as never });
    expect(quickBody(withReport, "own", "goal")).toEqual({ status: "confirmed" });
  });
});

describe("startSide: the team a quick question starts with", () => {
  it("the analysis' guess; without one the team chosen last, as a suggestion; else none", () => {
    expect(startSide(cand("a", 1000, 0.3, { suggested_side: "opponent" }), "own")).toEqual({ side: "opponent", suggested: false });
    expect(startSide(cand("b", 1000, 0.3, { suggested_side: null }), "own")).toEqual({ side: "own", suggested: true });
    expect(startSide(cand("c", 1000, 0.3, { suggested_side: null }), null)).toEqual({ side: null, suggested: false });
  });
});

const shell: ShellValue = {
  org: { id: "o1", name: "HC Beispiel", has_logo: false, primary_color: "#123456", my_role: "org_admin", features: [] },
  orgs: [],
  teams: [],
  team: null,
  mode: "staff",
  me: { name: "Coach", email: "coach@example.test" },
  setTeam: () => {},
} as unknown as ShellValue;
const match = { id: "m1", team_id: "t1", kind: "match", is_home: true, opponent: { name: "TV Seewald" }, opponent_colors: null, score_own: null, score_opponent: null, videos: [] } as never;

function render(l: CandidateList | null, messages: Record<string, unknown> = deCH, locale = "de-CH"): string {
  const client = new QueryClient();
  client.setQueryData(["shot-candidates", "m1"], l);
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        NextIntlClientProvider,
        { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>,
        createElement(ShellContext.Provider, { value: shell }, createElement(ShotQuick, { orgId: "o1", match })),
      ),
    ),
  );
}
const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

describe("the quick review screen", () => {
  it("shows the least sure shot first, its count, the team guess and four big answers on keys 1 to 4", () => {
    const html = render(list([cand("sure", 10_000, 0.8), cand("unsure", 20_000, 0.2, { suggested_side: "opponent" })]));
    expect(text(html)).toContain("1 von 2");
    expect(text(html)).toContain("Wie endete der Wurf?");
    for (const [a, k] of [["goal", 1], ["save", 2], ["miss", 3], ["none", 4]] as const) {
      expect(html).toMatch(new RegExp(`aria-keyshortcuts="${k}"[^>]*data-testid="shot-quick-${a}"`));
    }
    // the unsure one (opponent's) comes first: its team is preselected
    expect(html).toMatch(/aria-pressed="true"[^>]*data-testid="shot-quick-side-opponent"/);
    expect(html).not.toContain('data-testid="shot-quick-undo"'); // nothing to take back yet
  });

  it("says so when there is nothing to check", () => {
    expect(text(render(list([cand("done", 1000, 0.5, { status: "rejected" })])))).toContain("Keine Würfe zu prüfen");
  });

  it("speaks French and English", () => {
    expect(text(render(list([]), fr, "fr"))).toContain("Vérifier les tirs");
    expect(text(render(list([]), en, "en"))).toContain("Check shots");
  });
});

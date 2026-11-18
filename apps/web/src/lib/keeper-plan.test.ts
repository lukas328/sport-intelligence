import type { Schemas } from "@handball/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../messages/de-CH.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";
import { ShellContext, type ShellValue } from "@/components/shell/context";
import type { Stats } from "@/app/app/[orgId]/matches/[matchId]/analysis-views";
import { KeepersView } from "@/app/app/[orgId]/matches/[matchId]/m5-views";
import { NumbersView } from "@/app/app/[orgId]/matches/[matchId]/numbers-view";
import { hasFeature } from "./plan-features";

// The goalkeeper module is part of Team and Verein, not of Gratis (Lukas, 18.11.2026): a club
// without the plan feature `goalkeepers` sees the lock with the way to the plan where the
// goalkeeper figures would be, a Team club sees the figures.
const FREE = ["events"];
const TEAM = ["assistant", "events", "goalkeepers", "insights", "pdf_reports", "season", "share_links", "tactics", "tracking"];

const team = (goals = 0, saves = 0, goalsAgainst = 0) => ({
  goals,
  xg_shots: 0,
  xg_coverage: null,
  shots: goals,
  shots_blocked: 0,
  misses: 0,
  posts: 0,
  shooting_pct: null,
  saves,
  save_pct: saves + goalsAgainst ? saves / (saves + goalsAgainst) : null,
  goals_against: goalsAgainst,
  turnovers: 0,
  turnovers_by_type: {},
  seven_m_goals: 0,
  seven_m_shots: 0,
  fast_break_goals: 0,
  suspensions: 0,
  attack_efficiency: null,
  zones: {},
  goal_zones: {},
  by_situation: {},
  xg: 0,
});

const keeper = {
  side: "own" as const,
  player_id: "p-mia",
  number: 1,
  faced: 12,
  saves: 5,
  goals_against: 7,
  save_pct: 5 / 12,
  xg_against: 0,
  gsax: 0,
  seven_m: { faced: 2, saves: 1 },
  goal_zones: { TL: { faced: 4, saves: 1 } },
  shot_zones: { left_wing: { faced: 3, saves: 2 } },
};

// the API answers a club without the module with empty goalkeeper figures, the team's saves stay
function stats(withKeepers: boolean): Stats {
  return {
    own: team(8, 5, 7),
    opponent: team(7),
    players: {},
    goalkeepers: withKeepers ? { "own:p:p-mia": keeper } : {},
    timeline: { timed: true, score: [], best_run: {}, longest_own_drought_s: { seconds: 0 } },
    quality: { events: 20, sources: { manual: 20 } },
  };
}

const roster = [{ id: "e1", player_id: "p-mia", first_name: "Mia", last_name: "Probst", jersey_number: 1, main_position: "TW" }] as unknown as Schemas["RosterEntryOut"][];
const match = { id: "m1", team_id: "t1", season_id: "s1", source: "manual", report_extra: null, opponent: { name: "TV Beispiel" } } as unknown as Schemas["MatchOut"];

function shell(features: string[]): ShellValue {
  return {
    org: { id: "o1", name: "HC Beispiel", has_logo: false, primary_color: "#123456", my_role: "org_admin", features },
    orgs: [],
    teams: [],
    team: null,
    mode: "staff",
    me: { name: "Coach", email: "coach@example.test" },
    setTeam: () => {},
  };
}

function render(el: ReactElement, features: string[], messages: Record<string, unknown> = deCH, locale = "de-CH"): string {
  const qc = new QueryClient();
  // the roster the goalkeeper table reads (KeepersView asks for it)
  qc.setQueryData(["roster", "s1"], roster);
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client: qc },
      createElement(
        NextIntlClientProvider,
        { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>,
        createElement(ShellContext.Provider, { value: shell(features) }, el),
      ),
    ),
  );
}

const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/\s+/g, " ");
const numbers = (withKeepers: boolean) => createElement(NumbersView, { stats: stats(withKeepers), graphics: null, roster, orgId: "o1", match } as ComponentProps<typeof NumbersView>, null);
const keepers = (withKeepers: boolean) => createElement(KeepersView, { orgId: "o1", match, teamName: "Herren 1", stats: stats(withKeepers), names: { "p-mia": "Mia Probst" } });

describe("goalkeeper module by plan", () => {
  it("knows the feature from the club's list; an answer without a list keeps every feature", () => {
    expect(hasFeature(FREE, "goalkeepers")).toBe(false);
    expect(hasFeature(TEAM, "goalkeepers")).toBe(true);
    expect(hasFeature(undefined, "goalkeepers")).toBe(true);
  });

  it("Zahlen, free: the goalkeeper block is the lock with the hint and the way to the plan", () => {
    const html = render(numbers(false), FREE);
    expect(html).toContain('data-testid="numbers-keepers-locked"');
    expect(html).not.toContain('data-testid="numbers-keepers"');
    expect(text(html)).toContain("Torhüter-Auswertung im Team-Plan");
    expect(html).toContain('href="/app/o1/club/billing"');
  });

  it("Zahlen, Team: the goalkeeper table with the keeper's figures, no lock", () => {
    const html = render(numbers(true), TEAM);
    expect(html).toContain('data-testid="numbers-keepers"');
    expect(html).not.toContain('data-testid="keeper-lock"');
    expect(text(html)).toContain("Mia Probst");
  });

  it("Torhüter tab, free: the lock instead of the module", () => {
    const html = render(keepers(false), FREE);
    expect(html).toContain('data-testid="keeper-lock"');
    expect(html).not.toContain('data-testid="keeper-table"');
    expect(text(html)).toContain("Torhüter-Auswertung im Team-Plan");
  });

  it("Torhüter tab, Team: save rate per keeper and zones", () => {
    const html = render(keepers(true), TEAM);
    expect(html).toContain('data-testid="keeper-table"');
    expect(html).not.toContain('data-testid="keeper-lock"');
    expect(text(html)).toContain("42 %");
  });

  it("says it in French and English too", () => {
    expect(text(render(keepers(false), FREE, fr, "fr"))).toContain("Analyse des gardiens dans l'abonnement Équipe");
    expect(text(render(keepers(false), FREE, en, "en"))).toContain("Goalkeeper analysis in the Team plan");
  });
});

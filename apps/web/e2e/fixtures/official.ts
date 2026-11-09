/**
 * Answers of the official-data API (handball.ch behind it) in the shape the API returns them,
 * recorded by hand with invented clubs and people: real names from handball.ch must not land in
 * committed fixtures. The e2e specs answer the browser's requests with these (page.route), so the
 * screens can be tested without reaching handball.ch.
 */

export const CLUB = { id: 9001, name: "HC Seeblick", city: "Seedorf" };
const OTHER_CLUB = { id: 9002, name: "SG Bergtal", city: "Bergtal" };
// a club and team of the app that already took its official team over
export const CLAIMED_ORG = "00000000-0000-4000-8000-000000000a01";
export const CLAIMED_TEAM = "00000000-0000-4000-8000-000000000b01";

const team = (official_id: number, name: string, league: string, club = CLUB) => ({
  provider: "handball_ch",
  official_id,
  name,
  league,
  league_short: null,
  group_name: "Gruppe 2",
  season_id: 2026,
  club: { provider: "handball_ch", ...club },
  registered_club_id: club.id,
  status: "available" as const,
  team_id: null,
  organization_id: null,
});

export const searchHits = [
  team(71001, "HC Seeblick Herren 1", "Herren 3. Liga"),
  team(71002, "HC Seeblick Juniorinnen U18", "U18 Elite"),
  { ...team(72001, "SG Bergtal Herren", "Herren 2. Liga", OTHER_CLUB), status: "claimed" as const, team_id: CLAIMED_TEAM, organization_id: CLAIMED_ORG },
];

export const claimed = (organization_id: string, team_id: string) => ({
  status: "claimed",
  organization_id,
  team_id,
  created_organization: true,
  access_request_id: null,
  verification: "unverified",
  prefill: { matches_created: 18, matches_held_back: 0, results: 6, roster_suggestions: 3, report_suggestions: 1, other_suggestions: 0 },
});

export const accessRequested = {
  status: "access_requested",
  organization_id: CLAIMED_ORG,
  team_id: CLAIMED_TEAM,
  created_organization: false,
  access_request_id: "00000000-0000-4000-8000-000000000c01",
  verification: null,
  prefill: null,
};

export const joinRequested = {
  id: "00000000-0000-4000-8000-000000000d01",
  team_id: CLAIMED_TEAM,
  team_name: "SG Bergtal Herren",
  organization_id: CLAIMED_ORG,
  organization_name: OTHER_CLUB.name,
  status: "pending",
  created_at: "2026-11-09T10:00:00Z",
};

export const link = {
  linked: true,
  provider: "handball_ch",
  official_team_id: 71001,
  official_club_id: CLUB.id,
  official_group_id: 8801,
  official_season_id: 2026,
  league: "Herren 3. Liga",
  group_name: "Gruppe 2",
  synced_at: new Date(Date.now() - 20 * 60_000).toISOString(),
  standing: [
    { teamId: 71001, rank: 2, name: "HC Seeblick Herren 1", games: 6, goalDifference: 14, points: 9 },
    { teamId: 73001, rank: 1, name: "TV Talwiese", games: 6, goalDifference: 21, points: 10 },
  ],
  open_suggestions: 5,
  roster_stats: false,
};

const suggestion = (id: string, kind: string, payload: Record<string, unknown>) => ({
  id: `00000000-0000-4000-8000-0000000e${id.padStart(4, "0")}`,
  kind,
  status: "open",
  payload,
  created_at: "2026-11-09T09:00:00Z",
  resolved_at: null,
  blocked: null,
});

const stats = (goals: number) => ({ games: 6, goals, goals_7m: 1, attempts_7m: 2, suspensions_2min: 1, goalkeeper: false, saves: null });

export const suggestions = [
  // two players with the same official number: the coach changes one before taking the squad
  suggestion("1", "roster_add", { first_name: "Timo", last_name: "Brunner", jersey_number: 7, appearances: 6, stats: stats(21) }),
  suggestion("2", "roster_add", { first_name: "Jonas", last_name: "Amrein", jersey_number: 7, appearances: 4, stats: stats(9) }),
  // no official game yet: unticked
  suggestion("3", "roster_add", { first_name: "Nico", last_name: "Zemp", jersey_number: 23, appearances: 0, stats: null }),
  suggestion("4", "report", { opponent: "TV Talwiese", is_home: true, kickoff_at: "2026-11-01T17:00:00Z", score_own: 27, score_opponent: 25 }),
  suggestion("5", "match_new", { opponent: "HSG Rheinau", is_home: false, kickoff_at: "2026-11-22T18:30:00Z" }),
];

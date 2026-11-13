/**
 * Answers of the public entry API (handball.ch behind it) in the shape the API returns them,
 * recorded by hand with invented clubs, teams and people: the CI stack does not reach handball.ch,
 * and real names must not land in committed fixtures. The entry specs give these to the browser
 * (page.route), as official.spec.ts does for the signed-in official data.
 */

export const CLUB = { id: 9101, name: "SG Seeufer/Rebhalde", city: "Seeufer" };
const OTHER = { id: 9102, name: "HC Uferweg", city: "Uferweg" };

export const hit = (official_id: number, name: string, in_app = false, club = CLUB) => ({
  official_id,
  name,
  league: "Männer 1. Liga",
  group_name: "Gruppe 2",
  club,
  in_app,
  fuzzy: false,
});

export const HITS = [hit(81001, "SG Seeufer/Rebhalde"), hit(81002, "SG Seeufer/Rebhalde 2"), hit(82001, "HC Uferweg Herren", false, OTHER)];
/** a team someone has already taken over in the app */
export const TAKEN = hit(83001, "TV Rebhalde Herren", true, { id: 9103, name: "TV Rebhalde", city: "Rebhalde" });

const game = (days: number, opponent: string, own: number | null, opp: number | null, home = true) => ({
  opponent,
  home,
  own,
  opp,
  half_own: own == null ? null : Math.floor(own / 2),
  half_opp: opp == null ? null : Math.floor(opp / 2),
  kickoff_at: new Date(Date.now() + days * 86_400_000).toISOString(),
  venue: "Halle Seeufer",
});

export function preview(h: ReturnType<typeof hit>, scorers: boolean) {
  return {
    official_id: h.official_id,
    name: h.name,
    club: h.club,
    league: h.league,
    group_name: h.group_name,
    season: "2026/27",
    last: game(-3, "HC Uferweg", 28, 26),
    next: game(4, "TV Bergli", null, null, false),
    rank: 3,
    table: [
      { rank: 2, name: "TV Bergli", games: 8, points: 12, goal_difference: 21, own: false },
      { rank: 3, name: h.name, games: 8, points: 11, goal_difference: 9, own: true },
      { rank: 4, name: "HC Uferweg", games: 8, points: 9, goal_difference: -4, own: false },
    ],
    form: ["w", "w", "l", "w", "d"],
    run: { result: "w", count: 1 },
    played: 8,
    scorers: scorers
      ? [
          { name: "Lio Muster", goals: 41 },
          { name: "Nils Beispiel", goals: 33 },
        ]
      : [],
    scorer_games: scorers ? 8 : 0,
    in_app: h.in_app,
  };
}

/** what saving a taken team answers: an access request to its administrators */
export const accessRequested = {
  status: "access_requested",
  organization_id: "00000000-0000-4000-8000-000000000e01",
  team_id: "00000000-0000-4000-8000-000000000e02",
  created_organization: false,
  access_request_id: "00000000-0000-4000-8000-000000000e03",
  verification: null,
  prefill: null,
};

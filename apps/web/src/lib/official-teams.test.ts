import { describe, expect, it } from "vitest";
import { groupByClub, searchable, type OfficialTeam } from "./official-teams";

const hit = (id: number, name: string, club: number, status: OfficialTeam["status"] = "available"): OfficialTeam => ({
  official_id: id,
  name,
  league: "Männer 2. Liga",
  league_short: "M2",
  group_name: "Gruppe 1",
  season_id: 2026,
  club: { id: club, name: club === 1 ? "TV Thalwil" : "SG Horgen", city: null },
  registered_club_id: club,
  status,
});

describe("official team search", () => {
  it("groups by club, teams already in the app first, else in the search's order", () => {
    const g = groupByClub([hit(1, "TV Thalwil 2", 1), hit(2, "SG Horgen", 2), hit(3, "SG TV Thalwil", 1), hit(4, "TV Thalwil", 1, "claimed")]);
    expect(g.map((c) => c.name)).toEqual(["TV Thalwil", "SG Horgen"]);
    expect(g[0]!.teams.map((t) => t.name)).toEqual(["TV Thalwil", "TV Thalwil 2", "SG TV Thalwil"]);
  });
  it("needs three letters", () => {
    expect(searchable(" th ")).toBe(false);
    expect(searchable("thal")).toBe(true);
  });
});

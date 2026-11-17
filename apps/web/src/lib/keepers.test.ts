import { describe, expect, it } from "vitest";
import { againstCovered, ownKeepers } from "./keepers";

const row = (side: "own" | "opponent", player_id: string | null, number: number | null, saves: number, faced = saves) => ({ side, player_id, number, saves, faced });

describe("own goalkeepers (app review R4)", () => {
  const roster = [
    { player_id: "gk", jersey_number: 12, main_position: "TW" },
    { player_id: "rl", jersey_number: 7, main_position: "RL" },
  ];

  it("keeps the own team's keepers and numbers the roster does not know, nothing else", () => {
    const rows = [
      row("own", "gk", null, 11, 30),
      row("own", null, 16, 2, 4), // a number the roster does not know: its own row
      row("own", "rl", null, 1), // a field player credited with a save: no goalkeeper
      row("own", null, null, 0, 24), // goals against without a keeper: no row
      row("opponent", null, 1, 9, 20), // the other team's keeper
    ];
    expect(ownKeepers(rows, roster).map((k) => k.player_id ?? `#${k.number}`)).toEqual(["gk", "#16"]);
  });

  it("an unmarked roster cannot tell keepers from field players: every named own keeper", () => {
    const plain = roster.map((r) => ({ ...r, main_position: null }));
    expect(ownKeepers([row("own", "rl", null, 1), row("own", "gk", null, 5)], plain)).toHaveLength(2);
  });

  it("a column of goals against only when every goal against is credited", () => {
    expect(againstCovered([{ goals_against: 20 }, { goals_against: 4 }], 24)).toBe(true);
    expect(againstCovered([{ goals_against: 0 }], 24)).toBe(false);
  });
});

import { describe, expect, it } from "vitest";
import { similarTeams } from "./team-names";

const club = [{ name: "Herren 1" }, { name: "Damen" }, { name: "TV Thalwil Herren 2" }, { name: "U17 Junioren" }];

describe("similarTeams (K17)", () => {
  it("finds the same team written differently", () => {
    expect(similarTeams("herren", club).map((x) => x.name)).toEqual(["Herren 1"]);
    expect(similarTeams("Damen ", club).map((x) => x.name)).toEqual(["Damen"]);
    expect(similarTeams("U-17 Junioren", club).map((x) => x.name)).toEqual(["U17 Junioren"]);
    expect(similarTeams("TV Thalwil Damen", club).map((x) => x.name)).toEqual(["Damen"]);
  });

  it("keeps different teams apart", () => {
    expect(similarTeams("Herren 3", club)).toEqual([]);
    expect(similarTeams("Senioren", club)).toEqual([]);
    expect(similarTeams("", club)).toEqual([]);
  });
});

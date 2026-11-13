import { describe, expect, it } from "vitest";
import { chipsFromText } from "./scene-words";

describe("chipsFromText (B02, B19)", () => {
  it("reads the question of the test", () => {
    expect(chipsFromText("Wie viele Gegentore über rechts aussen in den letzten drei Spielen?")).toEqual(["conceded", "wing_right", "last_3"]);
  });
  it("reads short words", () => {
    expect(chipsFromText("Gegentore rechts aussen letzte drei Spiele")).toEqual(["conceded", "wing_right", "last_3"]);
    expect(chipsFromText("Tore vom Kreis letztes Spiel")).toEqual(["scored", "circle", "last_match"]);
    expect(chipsFromText("Ballverluste")).toEqual(["turnovers"]);
    expect(chipsFromText("Paraden Rückraum links")).toEqual(["saves", "back_left"]);
  });
  it("prefers conceded over goals and reads fr and en", () => {
    expect(chipsFromText("buts encaissés aile droite")).toEqual(["conceded", "wing_right"]);
    expect(chipsFromText("goals conceded left wing last 3 matches")).toEqual(["conceded", "wing_left", "last_3"]);
  });
  it("gives nothing for words it does not know", () => {
    expect(chipsFromText("Wetter morgen")).toEqual([]);
  });
});

describe("opponents and numbers in a sentence (UX test B19)", () => {
  it("finds the opponent among the team's opponents and a shirt number", async () => {
    const { extrasFromText } = await import("./scene-words");
    const opps = ["Handball Stäfa", "TV Thalwil-Gattikon"];
    expect(extrasFromText("Paraden gegen Stäfa", opps)).toEqual({ opponent: "Handball Stäfa" });
    expect(extrasFromText("Tore von Nummer 11", opps)).toEqual({ number: 11 });
    expect(extrasFromText("Gegentore #7 gegen Thalwil", opps)).toEqual({ opponent: "TV Thalwil-Gattikon", number: 7 });
    expect(extrasFromText("Gegentore über rechts aussen", opps)).toEqual({});
  });
});

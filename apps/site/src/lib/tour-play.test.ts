import { describe, expect, it } from "vitest";
import de from "@/messages/de";
import en from "@/messages/en";
import fr from "@/messages/fr";
import { DEFENCE, PLAY_BOX, PLAYERS, ballPath, passPath, percent, progressFor, stepAt } from "./tour-play";

// the play beside «So sieht es in der App aus» (BEFUNDE-4 U31)
describe("app tour play", () => {
  it("has one player per picture, named after the app's places in every language", () => {
    for (const m of [de, fr, en]) {
      expect(m.how.tourPlayers).toHaveLength(m.how.shots.length);
      expect(PLAYERS).toHaveLength(m.how.shots.length);
      expect(m.how.tourHint.length).toBeGreaterThan(10);
    }
    expect(de.how.tourPlayers).toEqual(["Spiele", "Szenen", "Saison", "Team"]);
  });

  it("keeps every player and defender inside the drawn part of the court", () => {
    const [x0, y0, w, h] = PLAY_BOX;
    for (const [x, y] of [...PLAYERS, ...DEFENCE]) {
      expect(x).toBeGreaterThan(x0 + 1);
      expect(x).toBeLessThan(x0 + w - 1);
      expect(y).toBeGreaterThan(y0 + 1);
      // room for the name under the dot
      expect(y).toBeLessThan(y0 + h - 2);
    }
    expect(percent([x0, y0])).toEqual({ left: "0.000%", top: "0.000%" });
    expect(percent([x0 + w, y0 + h])).toEqual({ left: "100.000%", top: "100.000%" });
  });

  it("turns the scroll into one step, each with the same stretch", () => {
    expect(stepAt(-0.2, 4)).toBe(0);
    expect(stepAt(Number.NaN, 4)).toBe(0);
    expect(stepAt(0, 4)).toBe(0);
    expect(stepAt(0.24, 4)).toBe(0);
    expect(stepAt(0.25, 4)).toBe(1);
    expect(stepAt(0.74, 4)).toBe(2);
    expect(stepAt(0.99, 4)).toBe(3);
    expect(stepAt(1.4, 4)).toBe(3);
  });

  it("lands a jump inside the step it was asked for", () => {
    for (let i = 0; i < 4; i++) expect(stepAt(progressFor(i, 4), 4)).toBe(i);
  });

  it("flies the ball along the passing lines, from player to player, both ways", () => {
    const fwd = ballPath(0, 3);
    expect(fwd[0]!.at).toEqual(PLAYERS[0]);
    expect(fwd.at(-1)!.at[0]).toBeCloseTo(PLAYERS[3]![0]);
    expect(fwd.at(-1)!.at[1]).toBeCloseTo(PLAYERS[3]![1]);
    expect(fwd[0]!.offset).toBe(0);
    expect(fwd.at(-1)!.offset).toBe(1);
    // offsets only grow (the animation's keyframes need that)
    for (let k = 1; k < fwd.length; k++) expect(fwd[k]!.offset).toBeGreaterThan(fwd[k - 1]!.offset);
    // it passes through the players in between
    expect(fwd.some((p) => Math.hypot(p.at[0] - PLAYERS[1]![0], p.at[1] - PLAYERS[1]![1]) < 1e-9)).toBe(true);
    const back = ballPath(2, 1);
    expect(back[0]!.at).toEqual(PLAYERS[2]);
    expect(back.at(-1)!.at[0]).toBeCloseTo(PLAYERS[1]![0]);
    expect(ballPath(1, 1)).toHaveLength(2);
  });

  it("draws a passing line between each two players in turn", () => {
    for (let i = 0; i < PLAYERS.length - 1; i++) {
      const d = passPath(i);
      expect(d.startsWith(`M${PLAYERS[i]![0].toFixed(2)} ${PLAYERS[i]![1].toFixed(2)}Q`)).toBe(true);
      expect(d.endsWith(`${PLAYERS[i + 1]![0].toFixed(2)} ${PLAYERS[i + 1]![1].toFixed(2)}`)).toBe(true);
    }
  });
});

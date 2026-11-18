import { describe, expect, it } from "vitest";
import { COURT } from "@handball/court";
import { ballAt } from "@/components/anlauf/ball";
import { sampleAt } from "@/components/anlauf/geometry";
import de from "@/messages/de";
import en from "@/messages/en";
import fr from "@/messages/fr";
import { demoGoals, demoScene, goalDistance, sceneGap } from "./demo";
import { MATCH } from "./things";
import { threeThings } from "./three-things";
import { matchPhases, preparedAnswers, seasonRightWing } from "./week";

describe("the demo week (U32)", () => {
  it("finds Saturday's turn in the report: 9:9 after 15:28, then four goals conceded in a row to 9:13", () => {
    const { phases, half } = matchPhases();
    expect(phases.map((p) => [p.key, p.score, `${p.own}:${p.opp}`])).toEqual([
      ["before", "9:9", "9:9"],
      ["run", "9:13", "0:4"],
      ["after", "27:29", "18:16"],
    ]);
    expect([phases[1]!.fromClock, phases[1]!.toClock]).toEqual(["15:28", "19:07"]);
    expect(phases[1]!.goals).toHaveLength(4);
    expect(phases[1]!.goals.every((g) => g.team === "opp")).toBe(true);
    expect(half).toBe("13:15");
    // the phases add up to the final score
    expect(phases.reduce((n, p) => n + p.own, 0)).toBe(27);
    expect(phases.reduce((n, p) => n + p.opp, 0)).toBe(29);
  });

  it("answers the prepared questions from the goals", () => {
    const a = preparedAnswers();
    expect(a.when).toMatchObject({ from: "15:28", to: "19:07", before: "9:9", after: "9:13", run: "0:4", rest: "18:16", n: 4 });
    expect(a.works.n).toBe(9);
    expect(a.works.of).toBe(27);
    expect(a.works.shots).toBe(MATCH.stats.own.zones.circle_centre.shots);
    expect(a.works.shooters.reduce((n, s) => n + s.n, 0)).toBeLessThanOrEqual(9);
  });

  it("follows the right wing over the season: 11 of 29, then 4, 4 and the start page's 3 of 26, the later ones marked as examples", () => {
    const s = seasonRightWing();
    expect(s.map((x) => [x.opp, x.n, x.of, x.example])).toEqual([
      ["TSV Nachtwind", 11, 29, false],
      ["BSV Wirbelstern", 4, 25, true],
      ["TV Rotdorn", 4, 27, true],
      ["TV Silberpfeil", 3, 26, true],
    ]);
    for (const x of s) {
      expect(x.dots).toHaveLength(x.of);
      expect(x.dots.filter((d) => d.ra)).toHaveLength(x.n);
    }
    for (const msgs of [de, fr, en]) expect(msgs.demo.nextExample.length).toBeGreaterThan(10);
  });

  it("plays every goal of the three things on the camera: fast breaks as a sprint, our own goals with us attacking", () => {
    const goals = demoGoals(MATCH);
    for (const thing of threeThings(goals)) {
      for (const g of thing.goals as ReturnType<typeof demoGoals>) {
        const scene = demoScene(g, "x");
        expect(scene.scorer?.team).toBe(g.team);
        expect(scene.ball.at(-1)).toMatchObject({ team: g.team, to: scene.duration });
        for (let i = 0; i <= 120; i++) expect(ballAt(scene, i / 120)).not.toBeNull();
        expect(scene.tracks.filter((x) => x.keeper)).toHaveLength(1);
        for (const tr of scene.tracks) {
          if (tr.team === "ref") continue;
          for (let i = 0; i <= 120; i++) {
            const [x, y] = sampleAt(tr.xy, i / 120);
            const d = Math.min(goalDistance([y, x]), goalDistance([y, 40 - x]));
            if (tr.keeper) expect(d).toBeLessThan(COURT.goalAreaRadius);
            else expect(d, `${g.id} ${tr.team} ${tr.number ?? "?"}`).toBeGreaterThanOrEqual(COURT.goalAreaRadius);
          }
        }
        const gap = sceneGap(scene);
        expect(gap).not.toBeNull();
        expect(gap!.at[0]).toBeGreaterThanOrEqual(0);
        expect(gap!.at[0]).toBeLessThanOrEqual(20);
      }
    }
  });

  it("puts our number 3 against their right wing, the player who answers in the team chat", () => {
    const g = (threeThings(demoGoals(MATCH))[0]!.goals as ReturnType<typeof demoGoals>)[0]!;
    const scene = demoScene(g, "x");
    const own = scene.tracks.filter((x) => x.team === "own" && !x.keeper);
    // the defender furthest to the attack's right (court y large in this half)
    const wingSide = own.reduce((a, b) => (a.xy[0]![1] > b.xy[0]![1] ? a : b));
    expect(wingSide.number).toBe(3);
    expect(de.home.chat.replyFrom).toBe("Nummer 3");
  });
});

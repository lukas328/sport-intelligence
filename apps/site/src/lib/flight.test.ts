import { describe, expect, it } from "vitest";
import { flightLayout, scoreAt } from "@/components/anlauf/flight-layout";
import { reportGoals } from "@/lib/demo";
import { demoView, MATCH } from "@/lib/things";
import de from "@/messages/de";
import en from "@/messages/en";
import fr from "@/messages/fr";

// U14: the line in the demo head says the score («Halbzeit 13:15», «Schluss 27:29»), as the
// figures further down do, not the goal difference
describe("the run of the match in the demo head", () => {
  const goals = reportGoals(demoView(de).goals);

  it("says the score at half-time and at the end, the same as the match report", () => {
    const half = MATCH.stats.timeline.score.filter((x) => x.clock_s <= 1800).at(-1)!;
    expect(scoreAt(goals, 30)).toBe(`${half.own}:${half.opp}`);
    expect(scoreAt(goals, 60)).toBe(`${MATCH.stats.timeline.final.own}:${MATCH.stats.timeline.final.opp}`);
    const L = flightLayout(goals, 1000, 120, 60, { half: de.match.flightHalf, end: de.match.flightEnd }, 48);
    expect(L.labels.map((l) => l.text)).toEqual([`Halbzeit ${half.own}:${half.opp}`, "Schluss 27:29"]);
  });

  it("uses the score in every language", () => {
    for (const m of [de, fr, en]) {
      expect(m.match.flightHalf).toContain("{score}");
      expect(m.match.flightEnd).toContain("{score}");
    }
  });
});

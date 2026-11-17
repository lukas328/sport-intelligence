import { describe, expect, it } from "vitest";
import court from "../../court/generated/court_geometry.json";
import { FREE_THROW_M, GOAL_AREA_M, MIN_GAP, POST_HIGH, POST_LOW, distToGoal, freeSpot, lineSpot, minTokenGap, mirrorDoc } from "./geometry";
import { TEMPLATES, templateDoc } from "./templates";
import type { Token } from "./format";

const isKeeper = (t: Token) => t.label === "TW";

describe("court geometry", () => {
  it("matches @handball/court", () => {
    expect(court.goal_area_radius).toBe(GOAL_AREA_M);
    expect(court.free_throw_radius).toBe(FREE_THROW_M);
    expect(court.keypoints.post_right_low).toEqual([40, POST_LOW]);
    expect(court.keypoints.post_right_high).toEqual([40, POST_HIGH]);
  });

  it("places spots on the 6 m and 9 m lines around the posts", () => {
    expect(lineSpot(6, 0)).toEqual([34, 10]);
    // every point of the generated goal-area line is 6 m from the goal mouth
    for (const [x, y] of court.lines.goal_area_right) expect(distToGoal(x!, y!)).toBeCloseTo(6, 2);
    for (const s of [-0.9, -0.5, -0.1, 0.3, 0.7, 0.95]) {
      const [x, y] = lineSpot(9, s);
      expect(distToGoal(x, y)).toBeCloseTo(9, 1);
    }
    // +s is the attacker's left (+y)
    expect(lineSpot(9, 0.5)[1]).toBeGreaterThan(10);
    expect(lineSpot(9, -0.5)[1]).toBeLessThan(10);
  });

  it("finds a free spot away from tokens and goal areas", () => {
    const tokens: Token[] = [{ id: "a", side: "own", label: "1", x: 30, y: 10 }];
    const [x, y] = freeSpot(tokens, [30, 10]);
    expect(Math.hypot(x - 30, y - 10)).toBeGreaterThanOrEqual(MIN_GAP);
    expect(distToGoal(x, y)).toBeGreaterThan(GOAL_AREA_M);
  });

  it("mirrors a play left to right", () => {
    const tpl = TEMPLATES.find((t) => t.id === "att_pivot_screen")!;
    const m = mirrorDoc(tpl.doc);
    const la = m.frames[0]!.tokens.find((t) => t.id === "la")!;
    expect(la.label).toBe("RA");
    expect(la.y).toBeCloseTo(20 - tpl.doc.frames[0]!.tokens.find((t) => t.id === "la")!.y, 5);
    expect(mirrorDoc(m)).toEqual(tpl.doc);
  });
});

describe("templates are handball-correct", () => {
  for (const tpl of TEMPLATES) {
    it(tpl.id, () => {
      tpl.doc.frames.forEach((f, i) => {
        const where = `${tpl.id} phase ${i + 1}`;
        // nobody overlaps, nobody leaves the court
        expect(minTokenGap(f.tokens), where).toBeGreaterThanOrEqual(MIN_GAP);
        for (const t of f.tokens) {
          expect(t.x, `${where} ${t.id}`).toBeGreaterThanOrEqual(tpl.doc.court === "half" ? 20.8 : 0.5);
          expect(t.x, `${where} ${t.id}`).toBeLessThanOrEqual(39.5);
          expect(t.y, `${where} ${t.id}`).toBeGreaterThanOrEqual(0.7);
          expect(t.y, `${where} ${t.id}`).toBeLessThanOrEqual(19.3);
          // only goalkeepers inside a goal area
          if (!isKeeper(t)) {
            expect(distToGoal(t.x, t.y), `${where} ${t.id} in the goal area`).toBeGreaterThan(GOAL_AREA_M + 0.2);
            expect(distToGoal(t.x, t.y, "left"), `${where} ${t.id} in the goal area`).toBeGreaterThan(GOAL_AREA_M + 0.2);
          } else expect(Math.min(distToGoal(t.x, t.y), distToGoal(t.x, t.y, "left"))).toBeLessThan(GOAL_AREA_M);
        }
        // every phase but the last has a note
        if (i < tpl.doc.frames.length) expect(f.note, where).not.toBe("");
      });
      for (const lang of ["de-CH", "fr", "en"] as const) {
        expect(tpl.notes[lang]).toHaveLength(tpl.doc.frames.length);
        expect(tpl.notes[lang].join(" ")).not.toMatch(/[—–ß]/);
      }
      expect(templateDoc(tpl, "fr").frames[0]!.note).toBe(tpl.notes.fr[0]);
    });
  }

  it("defences stand in front of the 6 m line in their shape, attackers around 9 m", () => {
    for (const tpl of TEMPLATES.filter((t) => t.category === "defence")) {
      const f = tpl.doc.frames[0]!;
      const defenders = f.tokens.filter((t) => t.side === "own" && !isKeeper(t));
      expect(defenders).toHaveLength(6);
      for (const d of defenders) {
        expect(distToGoal(d.x, d.y), `${tpl.id} ${d.id}`).toBeGreaterThan(6.3);
        expect(distToGoal(d.x, d.y), `${tpl.id} ${d.id}`).toBeLessThan(11);
      }
      const onLine = defenders.filter((d) => distToGoal(d.x, d.y) < 7.5).length;
      expect(onLine, tpl.id).toBe({ "6-0": 6, "5-1": 5, "3-2-1": 3, "4-2": 4 }[tpl.formation as "6-0"]);
      const back = f.tokens.filter((t) => ["RL", "RM", "RR"].includes(t.label));
      for (const b of back) expect(distToGoal(b.x, b.y), `${tpl.id} ${b.label}`).toBeGreaterThanOrEqual(9.5);
      const la = f.tokens.find((t) => t.label === "LA")!;
      expect(la.y, "the left wing is on the attacker's left").toBeGreaterThan(18);
    }
  });
});

import { describe, expect, it } from "vitest";
import { decided, type Side } from "./match-decided";

const side = (o: Partial<Side> = {}): Side => ({ shooting_pct: 0.5, save_pct: 0.3, turnovers: 10, fast_break_goals: 2, shots: 40, ...o });

describe("decided", () => {
  it("names the winner's two biggest edges", () => {
    const d = decided(side({ save_pct: 0.44, shooting_pct: 0.67, turnovers: 9 }), side({ save_pct: 0.24, shooting_pct: 0.49, turnovers: 11 }), "won");
    expect(d).toEqual({ side: "own", edges: ["saves", "shooting"] });
  });
  it("speaks of the opponent's edges after a loss", () => {
    const d = decided(side({ turnovers: 16 }), side({ turnovers: 8 }), "lost");
    expect(d).toEqual({ side: "opponent", edges: ["turnovers"] });
  });
  it("leaves rates out when there are too few shots", () => {
    expect(decided(side({ save_pct: 0.6, shots: 5 }), side({ save_pct: 0.2 }), "won")).toBeNull();
  });
  it("says nothing when no gap stands out", () => expect(decided(side(), side(), "won")).toBeNull());
});

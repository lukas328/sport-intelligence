import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { DRILLS } from "./drills";

const library = JSON.parse(readFileSync(join(__dirname, "..", "..", "..", "api", "src", "handball_api", "services", "drills.json"), "utf8")) as { id: string }[];

describe("the demo page's drills", () => {
  it("are the app's library drills, word for word", () => {
    for (const d of Object.values(DRILLS)) expect(d).toEqual(library.find((x) => x.id === d.id));
  });

  it("include the drill the app suggests first for goals after a fast break", () => {
    // services/training_tips.py drills_for(["transition_defence"]): drills made for the topic, basic first
    const hits = (library as { id: string; focus: string[]; level: string }[]).filter((d) => d.focus[0] === "transition_defence");
    const first = [...hits].sort((a, b) => Number(a.level !== "basic") - Number(b.level !== "basic"))[0]!;
    expect(first.id).toBe(DRILLS.transition_3v2_back.id);
  });
});

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { goalRuns, type MatchGraphics } from "@/lib/graphics";
import { threeThings } from "@/lib/three-things";

describe("the example match of the entry page (public/example/graphics.json)", () => {
  it("gives things to show: its goals carry places a coach tapped", () => {
    const g = JSON.parse(readFileSync(join(__dirname, "..", "..", "public", "example", "graphics.json"), "utf8")) as MatchGraphics;
    // only tapped places count (real-clip test of «Von wo?»); without them the example vanished
    expect(threeThings(goalRuns(g)).length).toBeGreaterThanOrEqual(2);
  });
});

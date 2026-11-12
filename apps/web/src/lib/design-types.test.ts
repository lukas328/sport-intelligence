/**
 * SPEC.md section 12, the rules a regex cannot check: the graphics take measured data only, so
 * nothing can draw a ball flight or a pass; page heads have no description.
 */
import { describe, expectTypeOf, it } from "vitest";
import type { GoalRun } from "@/components/anlauf/bundle";
import type { BallStretch, CameraScene, SceneTrack } from "@/components/anlauf/tactics-camera";
import type { PageHeader } from "@/components/ui/page-header";

describe("graphics take measured data only", () => {
  it("knows the ball only as who held it, never as a path", () => {
    expectTypeOf<BallStretch>().toEqualTypeOf<{ from: number; to: number; team: "own" | "opp"; number: number }>();
    expectTypeOf<CameraScene>().not.toHaveProperty("passes");
    expectTypeOf<CameraScene>().not.toHaveProperty("ballPath");
    expectTypeOf<SceneTrack["team"]>().toEqualTypeOf<"own" | "opp" | "ref">();
  });

  it("draws a goal as the scorer's run and a shot spot, the line to the goal straight", () => {
    expectTypeOf<GoalRun>().not.toHaveProperty("flight");
    expectTypeOf<GoalRun>().not.toHaveProperty("pass");
  });

  it("gives page heads no description", () => {
    expectTypeOf<Parameters<typeof PageHeader>[0]>().not.toHaveProperty("description");
  });
});

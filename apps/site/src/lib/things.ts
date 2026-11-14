/** The demo match as the pages need it: texts filled in, everything serialisable for client parts. */
import data from "../../public/demo/match.json";
import type { GoalRun } from "@/components/anlauf/bundle";
import type { ReportGoal } from "@/components/anlauf/flight-layout";
import type { CameraScene } from "@/components/anlauf/tactics-camera";
import { demoGoals, demoScene, type DemoGoal, type DemoMatch, reportGoals } from "@/lib/demo";
import { threeThings } from "@/lib/three-things";
import { fmt } from "@/lib/i18n";
import type { Messages } from "@/messages/de";

export const MATCH = data as unknown as DemoMatch;

export interface SceneRow {
  clock: string;
  text: string;
  estimated: boolean;
}

export interface ThingView {
  index: string;
  numeral: number;
  unit: string;
  text: string;
  sub: string;
  team: "own" | "opp";
  /** a bundle of runs, or the times only (turnovers from the report) */
  kind: "bundle" | "times";
  goals: GoalRun[];
  rest: GoalRun[];
  minutes: number[];
  label: string;
  note?: string;
  scenes: SceneRow[];
  scenesLabel: string;
}

export interface DemoView {
  own: string;
  opp: string;
  final: { own: number; opp: number };
  goals: DemoGoal[];
  report: ReportGoal[];
  things: ThingView[];
  scene: CameraScene;
  sceneGoal: DemoGoal;
}

const strip = (g: DemoGoal): GoalRun => ({ team: g.team, run: g.run, shot: g.shot, aim: g.aim, confirmed: g.confirmed, zone: g.zone, minute: g.minute });

export function demoView(m: Messages): DemoView {
  const goals = demoGoals(MATCH);
  const tx = m.things;
  const row = (g: DemoGoal): SceneRow => ({
    clock: g.clock,
    text: g.number != null ? fmt(m.demo.sceneRow, { clock: g.clock, number: g.number }) : fmt(m.demo.sceneRowNoNumber, { clock: g.clock }),
    estimated: !g.confirmed,
  });
  const bundleLabel = (gs: DemoGoal[]) => fmt(tx.bundleLabel, { n: gs.length, est: gs.filter((g) => !g.confirmed).length });
  // the app's rule (lib/three-things.ts): as many things as the goals allow, at most three
  const things: ThingView[] = threeThings(goals).map((t, i) => {
    const gs = t.goals as DemoGoal[];
    const first = gs.filter((g) => g.period === 1).length;
    const second = gs.length - first;
    const text =
      t.key === "conceded_zone"
        ? fmt(tx.concededText, { zone: tx.zones[t.zone as keyof typeof tx.zones] })
        : t.key === "conceded_fast_breaks"
          ? tx.fastText
          : fmt(tx.scoredText, { zone: tx.zones[t.zone as keyof typeof tx.zones] });
    return {
      index: fmt(tx.index, { i: i + 1 }),
      numeral: t.value,
      unit: fmt(tx.ofUnit, { total: t.of ?? 0 }),
      text,
      sub: fmt(tx.halves, { first, second }),
      team: t.team,
      kind: "bundle",
      goals: gs.map(strip),
      rest: (t.rest as DemoGoal[]).map(strip),
      minutes: [],
      label: bundleLabel(gs),
      scenes: gs.map(row),
      scenesLabel: fmt(tx.scenes, { n: gs.length }),
    };
  });
  const conceded = goals.filter((g) => g.team === "opp");
  const shown = (things[0]?.goals.length ? threeThings(goals)[0]!.goals : conceded) as DemoGoal[];
  const sceneGoal = shown.find((g) => g.confirmed) ?? shown[0] ?? goals[0]!;
  return {
    own: MATCH.own,
    opp: MATCH.opponent,
    final: MATCH.stats.timeline.final,
    goals,
    report: reportGoals(goals),
    things,
    scene: demoScene(sceneGoal, fmt(m.camera.goal, { opp: MATCH.opponent, clock: sceneGoal.clock })),
    sceneGoal,
  };
}

/** The demo match as the pages need it: texts filled in, everything serialisable for client parts. */
import data from "../../public/demo/match.json";
import type { GoalRun } from "@/components/anlauf/bundle";
import type { ReportGoal } from "@/components/anlauf/flight-layout";
import type { CameraScene } from "@/components/anlauf/tactics-camera";
import { demoGoals, demoScene, demoThings, type DemoGoal, type DemoMatch, reportGoals } from "@/lib/demo";
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
  const t = demoThings(MATCH, goals);
  const tx = m.things;
  const row = (g: DemoGoal): SceneRow => ({
    clock: g.clock,
    text: g.number != null ? fmt(m.demo.sceneRow, { clock: g.clock, number: g.number }) : fmt(m.demo.sceneRowNoNumber, { clock: g.clock }),
    estimated: !g.confirmed,
  });
  const bundleLabel = (gs: DemoGoal[]) => fmt(tx.bundleLabel, { n: gs.length, est: gs.filter((g) => !g.confirmed).length });
  const second = t.against.n - t.against.firstHalf;
  const things: ThingView[] = [
    {
      index: fmt(tx.index, { i: 1 }),
      numeral: t.against.n,
      unit: fmt(tx.againstUnit, { total: t.against.total }),
      text: fmt(tx.againstText, { zone: tx.zones[t.against.zone] }),
      sub: t.against.firstHalf >= second ? fmt(tx.againstSubFirst, { n: t.against.firstHalf }) : fmt(tx.againstSubSecond, { n: second }),
      team: "opp",
      kind: "bundle",
      goals: t.against.goals.map(strip),
      rest: t.against.rest.map(strip),
      minutes: [],
      label: bundleLabel(t.against.goals),
      scenes: t.against.goals.map(row),
      scenesLabel: fmt(tx.scenes, { n: t.against.n }),
    },
    {
      index: fmt(tx.index, { i: 2 }),
      numeral: t.fastBreak.n,
      unit: fmt(tx.fastUnit, { total: t.fastBreak.total }),
      text: tx.fastText,
      sub: fmt(tx.fastSub, { first: t.fastBreak.firstHalf, second: t.fastBreak.n - t.fastBreak.firstHalf }),
      team: "own",
      kind: "bundle",
      goals: t.fastBreak.goals.map(strip),
      rest: t.fastBreak.rest.map(strip),
      minutes: [],
      label: bundleLabel(t.fastBreak.goals),
      scenes: t.fastBreak.goals.map(row),
      scenesLabel: fmt(tx.scenes, { n: t.fastBreak.n }),
    },
    {
      index: fmt(tx.index, { i: 3 }),
      numeral: t.turnovers.n,
      unit: tx.turnUnit,
      text: tx.turnText,
      sub: fmt(tx.turnSub, { n: t.turnovers.window.n, from: t.turnovers.window.from, to: t.turnovers.window.to }),
      team: "own",
      kind: "times",
      goals: [],
      rest: [],
      minutes: t.turnovers.list.map((x) => x.minute),
      label: fmt(tx.turnLabel, { n: t.turnovers.n }),
      note: tx.turnNote,
      scenes: t.turnovers.list.map((x) => ({ clock: x.clock, text: fmt(m.demo.turnRow, { clock: x.clock }), estimated: false })),
      // from the match report: times only, no scenes (ANLAUF.md section 10)
      scenesLabel: "",
    },
  ];
  const sceneGoal = t.against.goals.find((g) => g.confirmed) ?? t.against.goals[0]!;
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

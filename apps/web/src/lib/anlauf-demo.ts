/**
 * Demo data of the Anlauf design (port of docs/design/ux-reset/assets/anlauf-demo.js) for the
 * component page /dev/anlauf and the component tests. Shapes, not values, are the contract:
 * every field names the API field it stands for (ANLAUF.md, section 10). Everything in here is
 * invented: source "demo".
 */
import type { GoalRun } from "@/components/anlauf/bundle";
import type { ReportGoal } from "@/components/anlauf/charts";
import type { Pt } from "@/components/anlauf/geometry";
import type { CameraScene, SceneTrack } from "@/components/anlauf/tactics-camera";

export const DEMO_SOURCE = "demo" as const;

function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

const ZN: Record<string, { u: [number, number]; v: [number, number] }> = {
  la: { u: [0.7, 2.8], v: [0.8, 3.0] },
  ra: { u: [17.2, 19.3], v: [0.8, 3.0] },
  rl: { u: [3.8, 7.6], v: [8.6, 11.2] },
  rm: { u: [8.4, 11.6], v: [8.8, 11.8] },
  rr: { u: [12.4, 16.2], v: [8.6, 11.2] },
  kr: { u: [8.0, 12.0], v: [6.0, 7.0] },
  m7: { u: [10, 10], v: [7, 7] },
  gs: { u: [6.5, 13.5], v: [4.5, 7.5] },
};

function goals(seed: number, team: GoalRun["team"], spec: Record<string, number>, estimated: number): GoalRun[] {
  const R = rng(seed);
  const out: GoalRun[] = [];
  for (const [z, count] of Object.entries(spec)) {
    for (let i = 0; i < count; i++) {
      const Z = ZN[z]!;
      const u = Z.u[0] + R() * (Z.u[1] - Z.u[0]);
      const v = Z.v[0] + R() * (Z.v[1] - Z.v[0]);
      let pts: Pt[];
      if (z === "la" || z === "ra") {
        const side = z === "la" ? -1 : 1;
        pts = [
          [u + side * (0.2 + R() * 0.6), v + 6 + R() * 4],
          [u + side * (0.6 + R()), v + 3 + R() * 1.5],
          [u - side * R() * 0.6, v + 1.2],
          [u, v],
        ];
      } else if (z === "gs") {
        const u0 = 3 + R() * 14;
        pts = [
          [u0, 19.6],
          [u0 + (u - u0) * 0.35 + (R() - 0.5) * 2, 14 + R() * 2],
          [u + (R() - 0.5) * 1.5, v + 3.5],
          [u, v],
        ];
      } else if (z === "kr") {
        const s = R() < 0.5 ? -1 : 1;
        pts = [
          [u + s * (2.5 + R() * 2), v + 0.4 + R() * 0.6],
          [u + s * (1.2 + R()), v + 0.2 + R() * 0.5],
          [u + s * 0.4, v + 0.1],
          [u, v],
        ];
      } else if (z === "m7") {
        pts = [
          [u, v + 2.2],
          [u, v + 1.1],
          [u, v],
        ];
      } else {
        const dx = (R() - 0.5) * 7;
        pts = [
          [u + dx, v + 4.5 + R() * 3],
          [u + dx * 0.55, v + 2.6 + R()],
          [u + dx * 0.15, v + 0.9],
          [u, v],
        ];
      }
      const run = pts.map((p) => [Math.max(0.3, Math.min(19.7, p[0])), Math.max(0.3, Math.min(19.8, p[1]))] as Pt);
      out.push({ team, zone: z, run, shot: [u, v], aim: [8.8 + R() * 2.4, 0], confirmed: true, minute: Math.round(R() * 60) });
    }
  }
  for (let e = 0; e < estimated; e++) out[Math.floor(R() * out.length)]!.confirmed = false;
  return out;
}

export const DEMO_GOALS = {
  them: goals(31, "opp", { ra: 9, rl: 3, rm: 2, la: 2, rr: 1, kr: 1 }, 3),
  us: goals(47, "own", { kr: 7, la: 3, ra: 3, rl: 3, rm: 3, rr: 3, m7: 2, gs: 2 }, 3),
  themFastBreaks: goals(53, "opp", { gs: 6 }, 2),
};

/**
 * The demo match of SPEC.md section 10: HC Zürichsee against TSV Thalwil 26:18 (13:9), with the
 * goal sequence of the report (Torfolge 2:1, 5:4, 9:6, 13:9; 15:12, 17:15, 21:16, 26:18).
 */
export const DEMO_RESULT = { own: 26, opp: 18, halftime: [13, 9] } as const;

const SEQUENCE: [minute: number, own: number, opp: number][] = [
  [0, 0, 0], [5, 2, 1], [11, 5, 4], [19, 9, 6], [30, 13, 9], [37, 15, 12], [44, 17, 15], [51, 21, 16], [60, 26, 18],
];

/** report.goals[]: the goals between two marks of the sequence, spread evenly, ours first */
function reportOf(seq: typeof SEQUENCE): ReportGoal[] {
  const out: ReportGoal[] = [];
  for (let i = 1; i < seq.length; i++) {
    const [m0, o0, t0] = seq[i - 1]!;
    const [m1, o1, t1] = seq[i]!;
    const n = o1 - o0 + (t1 - t0);
    let own = o1 - o0;
    let opp = t1 - t0;
    for (let j = 0; j < n; j++) {
      // keep the running share: ours when we are behind our share of this stretch
      const team: ReportGoal["team"] = opp === 0 || (own > 0 && own / (own + opp) >= 0.5) ? "own" : "opp";
      if (team === "own") own--;
      else opp--;
      out.push({ minute: Math.round((m0 + ((m1 - m0) * (j + 0.5)) / n) * 10) / 10, team });
    }
  }
  return out;
}

export const DEMO_REPORT: ReportGoal[] = reportOf(SEQUENCE);

export const DEMO_PHASE: [number, number] = [38, 44];

type Raw = [number, Pt[], 0 | 1];

function scene(clock: [number, number], us: Raw[], them: Raw[], ref: Pt[]): SceneTrack[] {
  const tr = (team: "own" | "opp") => (p: Raw): SceneTrack => ({ team, number: p[2] ? p[0] : null, xy: p[1] });
  return [...us.map(tr("own")), ...them.map(tr("opp")), { team: "ref", xy: ref }];
}

/** A goal conceded over the right wing, 39:55; the ball was found in three stretches. */
export const DEMO_SCENE_RA: CameraScene = {
  clock: 39 * 60 + 49,
  duration: 6,
  tracks: scene(
    [39, 49],
    [
      [1, [[1.0, 11.2], [0.9, 10.4], [0.8, 9.6], [0.7, 9.1]], 1],
      [7, [[5.4, 2.0], [5.8, 2.4], [6.6, 3.2], [7.6, 4.2], [8.4, 5.0]], 1],
      [13, [[6.6, 7.4], [6.9, 7.1], [7.4, 7.0], [7.9, 7.3]], 0],
      [4, [[7.0, 10.8], [7.2, 10.2], [7.5, 9.8], [7.6, 9.6]], 0],
      [10, [[6.8, 12.6], [7.0, 11.8], [7.3, 11.1], [7.4, 10.8]], 0],
      [11, [[6.8, 15.0], [7.0, 14.2], [7.2, 13.5], [7.3, 13.1]], 0],
      [8, [[5.8, 17.8], [5.9, 17.2], [6.2, 16.6], [6.4, 16.2]], 0],
    ],
    [
      [5, [[1.4, 0.5], [0.8, 0.8], [1.1, 1.2], [2.0, 1.6], [3.0, 2.2], [3.9, 2.9]], 1],
      [9, [[15.6, 9.0], [14.6, 7.8], [13.2, 6.5], [11.8, 5.6], [10.5, 5.0]], 1],
      [14, [[14.8, 12.8], [14.0, 11.6], [13.0, 10.6], [12.1, 10.0]], 1],
      [22, [[13.2, 17.4], [12.6, 16.4], [11.6, 15.3], [10.9, 14.6]], 1],
      [3, [[0.8, 19.5], [1.0, 19.2], [1.3, 18.9], [1.6, 18.6]], 0],
      [18, [[6.2, 12.6], [6.3, 11.4], [6.6, 9.8], [6.7, 8.4], [6.6, 7.4]], 0],
    ],
    [[12.0, 1.6], [10.8, 1.4], [9.6, 1.5]],
  ),
  ball: [
    { from: 0, to: 1.3, team: "opp", number: 14 },
    { from: 1.5, to: 2.6, team: "opp", number: 9 },
    { from: 4.6, to: 6, team: "opp", number: 5 },
  ],
  scorer: { team: "opp", number: 5 },
  shot: [3.9, 2.9],
  aim: [0.15, 8.9],
  confirmed: true,
  label: "Tor Thalwil 39:55",
};

/** Our goal from the circle, 18:02: here the ball was not found in the picture. */
export const DEMO_SCENE_KR: CameraScene = {
  clock: 17 * 60 + 56,
  duration: 6,
  tracks: scene(
    [17, 56],
    [
      [8, [[7.4, 12.6], [7.0, 12.0], [6.6, 11.2], [6.2, 10.4], [5.9, 9.9]], 1],
      [10, [[10.8, 13.4], [10.4, 12.4], [10.2, 11.6], [10.1, 11.2]], 1],
      [4, [[11.2, 6.4], [10.6, 6.8], [10.0, 7.4], [9.6, 7.8]], 0],
      [11, [[10.6, 16.6], [10.2, 16.0], [9.8, 15.4], [9.6, 15.0]], 0],
      [3, [[2.4, 1.0], [2.6, 1.4], [2.8, 1.8], [3.0, 2.0]], 1],
      [7, [[2.6, 19.0], [2.8, 18.6], [3.0, 18.2], [3.1, 18.0]], 0],
    ],
    [
      [1, [[0.9, 10.6], [1.0, 10.4], [1.1, 10.2], [1.2, 10.1]], 1],
      [6, [[4.0, 3.0], [4.1, 3.4], [4.2, 3.7], [4.2, 3.9]], 0],
      [12, [[6.2, 6.6], [6.4, 7.2], [6.4, 7.6], [6.3, 7.9]], 0],
      [15, [[6.7, 9.0], [6.6, 9.6], [6.4, 10.0], [6.3, 10.2]], 0],
      [17, [[6.6, 11.8], [6.6, 11.6], [6.5, 11.6], [6.5, 11.7]], 1],
      [19, [[6.3, 13.8], [6.3, 13.6], [6.3, 13.5], [6.3, 13.4]], 0],
      [21, [[4.4, 16.4], [4.4, 16.3], [4.4, 16.2], [4.4, 16.1]], 0],
    ],
    [[13.0, 18.6], [12.0, 18.8], [11.2, 18.8]],
  ),
  ball: [],
  scorer: { team: "own", number: 8 },
  shot: [5.9, 9.9],
  aim: [0.15, 9.4],
  confirmed: false,
  label: "Tor Zürichsee 18:02",
};

export const DEMO_SEASON = {
  diff: [
    { label: "Rüti", diff: 5 },
    { label: "Wädenswil", diff: -3 },
    { label: "Horgen", diff: 10 },
    { label: "Meilen", diff: 1 },
    { label: "Stäfa", diff: -7 },
    { label: "Thalwil", diff: 8 },
  ],
  themes: [
    { title: "Gegentore über rechts aussen", series: [5, 5, 9], team: "opp" as const },
    { title: "Ballverluste", series: [10, 15, 11], team: "own" as const },
    { title: "Tore vom Kreis", series: [3, 4, 7], team: "own" as const },
  ],
};

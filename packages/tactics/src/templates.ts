/**
 * Built-in starting points for the play library (BRIEF 8.3 "Vorlagen"). Basic, widely taught handball
 * set-ups; the attacked goal is on the right (x = 40). Names are i18n keys (`tactics.tpl_<id>`).
 */
import { TACTICS_FORMAT_VERSION, type Frame, type PlayDoc, type Token } from "./format";

export interface Template {
  id: string;
  category: "attack" | "defence" | "fast_break" | "set_piece";
  formation: string | null;
  tags: string[];
  doc: PlayDoc;
}

const GOAL_X = 40;
const own = (id: string, label: string, x: number, y: number): Token => ({ id, side: "own", label, x, y });
const opp = (id: string, label: string, x: number, y: number): Token => ({ id, side: "opp", label, x, y });
const frame = (tokens: Token[], extra: Partial<Frame> = {}): Frame => ({ tokens, ball: null, arrows: [], note: "", duration_ms: 2000, ...extra });
const doc = (...frames: Frame[]): PlayDoc => ({ formatVersion: TACTICS_FORMAT_VERSION, court: "half", frames });

/** Defenders in front of their goal (the opponent attacks to the right, we defend the right goal). */
function defence(formation: "6-0" | "5-1" | "3-2-1" | "4-2"): Token[] {
  const line = (n: number, depth: number, ys: number[]) => ys.slice(0, n).map((y, i) => [GOAL_X - depth - Math.abs(y - 10) * 0.12, y, i] as const);
  const spots: (readonly [number, number])[] = {
    "6-0": line(6, 6.6, [2.5, 6, 8.8, 11.2, 14, 17.5]).map(([x, y]) => [x, y] as const),
    "5-1": [...line(5, 6.6, [2.5, 6.5, 10, 13.5, 17.5]).map(([x, y]) => [x, y] as const), [GOAL_X - 10, 10] as const],
    "3-2-1": [
      [GOAL_X - 6.6, 3] as const,
      [GOAL_X - 6.4, 10] as const,
      [GOAL_X - 6.6, 17] as const,
      [GOAL_X - 8.8, 6.5] as const,
      [GOAL_X - 8.8, 13.5] as const,
      [GOAL_X - 11, 10] as const,
    ],
    "4-2": [
      ...line(4, 6.6, [3, 8.2, 11.8, 17]).map(([x, y]) => [x, y] as const),
      [GOAL_X - 9.5, 6.5] as const,
      [GOAL_X - 9.5, 13.5] as const,
    ],
  }[formation];
  return [own("tw", "TW", GOAL_X - 0.8, 10), ...spots.map(([x, y], i) => own(`d${i + 1}`, String(i + 1), x, y))];
}

/** Six attackers in a 3-3 set-up against the right goal. */
function attack33(): Token[] {
  return [
    opp("la", "LA", GOAL_X - 3, 1.5),
    opp("rl", "RL", GOAL_X - 10.5, 5),
    opp("rm", "RM", GOAL_X - 11, 10),
    opp("rr", "RR", GOAL_X - 10.5, 15),
    opp("ra", "RA", GOAL_X - 3, 18.5),
    opp("km", "KM", GOAL_X - 6.2, 9),
  ];
}

function ownAttack(): Token[] {
  return attack33().map((t) => ({ ...t, side: "own" as const }));
}

export const TEMPLATES: Template[] = [
  { id: "def_6_0", category: "defence", formation: "6-0", tags: ["6:0", "Abwehr"], doc: doc(frame([...defence("6-0"), ...attack33()])) },
  { id: "def_5_1", category: "defence", formation: "5-1", tags: ["5:1", "Abwehr"], doc: doc(frame([...defence("5-1"), ...attack33()])) },
  { id: "def_3_2_1", category: "defence", formation: "3-2-1", tags: ["3:2:1", "Abwehr"], doc: doc(frame([...defence("3-2-1"), ...attack33()])) },
  { id: "def_4_2", category: "defence", formation: "4-2", tags: ["4:2", "Abwehr"], doc: doc(frame([...defence("4-2"), ...attack33()])) },
  {
    id: "att_cross_back",
    category: "attack",
    formation: "3-3",
    tags: ["Kreuzen", "Rückraum"],
    doc: (() => {
      const start = ownAttack();
      const f1 = frame(start, {
        ball: { x: GOAL_X - 11, y: 10 },
        arrows: [
          { kind: "dribble", points: [[GOAL_X - 11, 10], [GOAL_X - 9.5, 13]] },
          { kind: "run", points: [[GOAL_X - 10.5, 15], [GOAL_X - 10, 9]] },
        ],
        note: "RM zieht nach rechts, RR kreuzt hinter RM in die Mitte.",
      });
      const f2 = frame(
        start.map((t) => (t.id === "rm" ? { ...t, x: GOAL_X - 9.5, y: 13 } : t.id === "rr" ? { ...t, x: GOAL_X - 10, y: 9 } : t)),
        {
          ball: { x: GOAL_X - 9.5, y: 13 },
          arrows: [{ kind: "pass", points: [[GOAL_X - 9.5, 13], [GOAL_X - 10, 9]] }],
          note: "Übergabe an RR, der in die Lücke stösst.",
        },
      );
      const f3 = frame(
        f2.tokens.map((t) => (t.id === "rr" ? { ...t, x: GOAL_X - 8.5, y: 8.5 } : t)),
        { ball: { x: GOAL_X - 8.5, y: 8.5 }, note: "Wurf oder Abspiel an KM." },
      );
      return doc(f1, f2, f3);
    })(),
  },
  {
    id: "att_pivot_screen",
    category: "attack",
    formation: "3-3",
    tags: ["Sperre", "Kreis"],
    doc: (() => {
      const start = ownAttack();
      const f1 = frame(start, {
        ball: { x: GOAL_X - 10.5, y: 5 },
        arrows: [{ kind: "screen", points: [[GOAL_X - 6.2, 9], [GOAL_X - 8, 6.5]] }],
        note: "KM stellt die Sperre für RL.",
      });
      const f2 = frame(
        start.map((t) => (t.id === "km" ? { ...t, x: GOAL_X - 8, y: 6.5 } : t)),
        {
          ball: { x: GOAL_X - 10.5, y: 5 },
          arrows: [{ kind: "dribble", points: [[GOAL_X - 10.5, 5], [GOAL_X - 9, 8.5]] }],
          note: "RL geht an der Sperre vorbei durch.",
        },
      );
      return doc(f1, f2);
    })(),
  },
  {
    id: "fb_first_wave",
    category: "fast_break",
    formation: null,
    tags: ["Gegenstoss", "1. Welle"],
    doc: (() => {
      const start = [own("tw", "TW", 1, 10), own("la", "LA", 8, 1.5), own("ra", "RA", 8, 18.5), own("rm", "RM", 10, 10)];
      const f1 = frame(start, {
        ball: { x: 1, y: 10 },
        arrows: [
          { kind: "run", points: [[8, 1.5], [33, 3]] },
          { kind: "run", points: [[8, 18.5], [33, 17]] },
          { kind: "pass", points: [[1, 10], [20, 5]] },
        ],
        note: "Aussen laufen sofort, TW spielt den langen Ball.",
      });
      return { ...doc(f1, frame(start.map((t) => (t.id === "la" ? { ...t, x: 33, y: 3 } : t.id === "ra" ? { ...t, x: 33, y: 17 } : t)), { ball: { x: 33, y: 3 } })), court: "full" as const };
    })(),
  },
  {
    id: "sp_free_throw",
    category: "set_piece",
    formation: null,
    tags: ["Freiwurf", "9 m"],
    doc: doc(
      frame([...ownAttack().map((t) => (t.id === "rm" ? { ...t, x: GOAL_X - 9.2, y: 10 } : t)), ...defence("6-0").slice(1).map((t) => ({ ...t, side: "opp" as const }))], {
        ball: { x: GOAL_X - 9.2, y: 10 },
        note: "Freiwurf an der 9-m-Linie: Block für den Wurf aus der Mitte.",
      }),
    ),
  },
];

export function searchTemplates(query: string, category?: Template["category"]): Template[] {
  const q = query.trim().toLowerCase();
  return TEMPLATES.filter(
    (t) =>
      (!category || t.category === category) &&
      (!q || t.id.includes(q) || (t.formation ?? "").includes(q) || t.tags.some((g) => g.toLowerCase().includes(q))),
  );
}

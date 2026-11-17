/**
 * Built-in starting points for the play library (BRIEF 8.3 "Vorlagen"): basic, widely taught handball
 * set-ups. The attacked goal is on the right (x = 40), facing it +y is left, so the left wing (LA)
 * stands at a high y. Every position comes from `lineSpot` (court geometry): defenders in front of
 * the 6 m line in the shape of their formation, back-court attackers around 9 to 12 m, wings at the
 * side lines, only goalkeepers inside the goal area. A test checks these rules and that no two
 * players overlap. Names are i18n keys (`tactics.tpl_<id>`), the notes per phase are in de-CH, fr, en.
 */
import { TACTICS_FORMAT_VERSION, type Arrow, type Frame, type PlayDoc, type Side, type Token } from "./format";
import { GOAL_X, lineSpot } from "./geometry";

export type TemplateLang = "de-CH" | "fr" | "en";

export interface Template {
  id: string;
  category: "attack" | "defence" | "fast_break" | "set_piece";
  formation: string | null;
  tags: string[];
  doc: PlayDoc;
  /** one note per phase in each language (the doc carries the de-CH ones) */
  notes: Record<TemplateLang, string[]>;
}

type P = readonly [number, number];
const tok = (side: Side, id: string, label: string, [x, y]: P): Token => ({ id, side, label, x, y });
const frame = (tokens: Token[], extra: Partial<Frame> = {}): Frame => ({ tokens, ball: null, arrows: [], note: "", duration_ms: 2000, ...extra });
const arrow = (kind: Arrow["kind"], ...points: P[]): Arrow => ({ kind, points: points.map(([x, y]) => [x, y] as [number, number]) });
/** tokens of a frame with some of them moved */
const moved = (tokens: Token[], to: Record<string, P>): Token[] => tokens.map((t) => (to[t.id] ? { ...t, x: to[t.id]![0], y: to[t.id]![1] } : t));
const at = (tokens: Token[], id: string): P => {
  const t = tokens.find((k) => k.id === id)!;
  return [t.x, t.y];
};

const GOALKEEPER: P = [GOAL_X - 0.7, 10];
const LINE = 6.8; // defenders stand a step in front of the 6 m line

export type Formation = "6-0" | "5-1" | "3-2-1" | "4-2";

/** Defence spots as [distance to the goal mouth, position along the line]; numbered from the left of the board. */
const DEFENCE: Record<Formation, (readonly [number, number])[]> = {
  "6-0": [0.82, 0.49, 0.16, -0.16, -0.49, -0.82].map((s) => [LINE, s] as const),
  "5-1": [...[0.8, 0.4, 0, -0.4, -0.8].map((s) => [LINE, s] as const), [9.8, 0]],
  "3-2-1": [[LINE, 0.62], [LINE, 0], [LINE, -0.62], [8.8, 0.33], [8.8, -0.33], [10.6, 0]],
  "4-2": [...[0.7, 0.24, -0.24, -0.7].map((s) => [LINE, s] as const), [9.6, 0.28], [9.6, -0.28]],
};

/** Goalkeeper and six defenders of a formation in front of the right goal. */
export function defence(formation: Formation, side: Side = "own"): Token[] {
  return [tok(side, "tw", "TW", GOALKEEPER), ...DEFENCE[formation].map(([d, s], i) => tok(side, `d${i + 1}`, String(i + 1), lineSpot(d, s)))];
}

/**
 * Six attackers in a 3:3 against the right goal. Against an advanced defender the centre back
 * starts deeper (the defender stands between him and the goal); the pivot stands at the 6 m line
 * in a gap of the defence.
 */
export function attack(side: Side = "opp", against: Formation = "6-0"): Token[] {
  const rm = { "6-0": 11, "5-1": 11.9, "3-2-1": 12.4, "4-2": 11 }[against];
  const km: P = { "6-0": lineSpot(6.3, 0), "5-1": lineSpot(6.4, 0.2), "3-2-1": lineSpot(6.3, 0.3), "4-2": lineSpot(6.3, 0) }[against];
  return [
    tok(side, "la", "LA", [36.2, 19.2]),
    tok(side, "rl", "RL", lineSpot(10.8, 0.36)),
    tok(side, "rm", "RM", lineSpot(rm, 0)),
    tok(side, "rr", "RR", lineSpot(10.8, -0.36)),
    tok(side, "ra", "RA", [36.2, 0.8]),
    tok(side, "km", "KM", km),
  ];
}

const doc = (frames: Frame[], notes: Record<TemplateLang, string[]>, court: PlayDoc["court"] = "half"): { doc: PlayDoc; notes: Record<TemplateLang, string[]> } => ({
  doc: { formatVersion: TACTICS_FORMAT_VERSION, court, frames: frames.map((f, i) => ({ ...f, note: notes["de-CH"][i] ?? "" })) },
  notes,
});

function defenceTemplate(id: string, formation: Formation, tag: string, notes: Record<TemplateLang, string>): Template {
  const tokens = [...defence(formation), ...attack("opp", formation)];
  return {
    id,
    category: "defence",
    formation,
    tags: [tag, "Abwehr"],
    ...doc([frame(tokens, { ball: { x: at(tokens, "rm")[0], y: at(tokens, "rm")[1] } })], {
      "de-CH": [notes["de-CH"]],
      fr: [notes.fr],
      en: [notes.en],
    }),
  };
}

function crossBack(): Template {
  const start = [...attack("own"), ...defence("6-0", "opp")];
  const rm = at(start, "rm");
  const rr = at(start, "rr");
  const rmEnd: P = [30.6, 7.9];
  const rrEnd: P = [28.2, 11.6];
  const f1 = frame(start, { ball: { x: rm[0], y: rm[1] }, arrows: [arrow("dribble", rm, rmEnd), arrow("run", rr, [28.2, 7.4], rrEnd)] });
  const s2 = moved(start, { rm: rmEnd, rr: rrEnd, d4: [32.4, 8.3] });
  const gap: P = [31.6, 10.3];
  const f2 = frame(s2, { ball: { x: rmEnd[0], y: rmEnd[1] }, arrows: [arrow("pass", rmEnd, rrEnd), arrow("run", rrEnd, gap)] });
  const s3 = moved(s2, { rr: gap, d3: [33.3, 12.1] });
  const f3 = frame(s3, { ball: { x: gap[0], y: gap[1] }, duration_ms: 2500 });
  return {
    id: "att_cross_back",
    category: "attack",
    formation: "3-3",
    tags: ["Kreuzen", "Rückraum"],
    ...doc([f1, f2, f3], {
      "de-CH": [
        "RM stösst mit Ball nach rechts, RR kreuzt hinter RM in die Mitte.",
        "RM spielt RR im Lauf an, Verteidiger 4 ist an RM gebunden.",
        "RR stösst in die Lücke zwischen 3 und 4: Wurf aus 8 m oder Abspiel an KM.",
      ],
      fr: [
        "Le DC part balle en main vers la droite, l'AR croise derrière lui vers le centre.",
        "Le DC passe à l'AR lancé, le défenseur 4 reste fixé sur le DC.",
        "L'AR attaque l'intervalle entre 3 et 4 : tir à 8 m ou passe au pivot.",
      ],
      en: [
        "CB drives right with the ball, RB crosses behind CB into the middle.",
        "CB passes to the running RB, defender 4 is tied to CB.",
        "RB attacks the gap between 3 and 4: shot from 8 m or pass to the pivot.",
      ],
    }),
  };
}

function pivotScreen(): Template {
  const start = [...attack("own"), ...defence("6-0", "opp")];
  const rm = at(start, "rm");
  const rl = at(start, "rl");
  const km = at(start, "km");
  const screen: P = [33.5, 13.9];
  const f1 = frame(start, { ball: { x: rm[0], y: rm[1] }, arrows: [arrow("pass", rm, rl), arrow("screen", km, screen)] });
  const s2 = moved(start, { km: screen });
  const through: P = [31.4, 12.7];
  const f2 = frame(s2, { ball: { x: rl[0], y: rl[1] }, arrows: [arrow("dribble", rl, through)] });
  const s3 = moved(s2, { rl: through, d3: [32.9, 11.2] });
  const f3 = frame(s3, { ball: { x: through[0], y: through[1] }, duration_ms: 2500 });
  return {
    id: "att_pivot_screen",
    category: "attack",
    formation: "3-3",
    tags: ["Sperre", "Kreis"],
    ...doc([f1, f2, f3], {
      "de-CH": [
        "RM spielt zu RL, KM stellt die Sperre innen an Verteidiger 2.",
        "RL geht innen an der Sperre vorbei in die Lücke.",
        "Wurf von RL aus 9 m oder Abspiel an KM, der sich von der Sperre löst.",
      ],
      fr: [
        "Le DC passe à l'arrière gauche, le pivot pose l'écran à l'intérieur du défenseur 2.",
        "L'arrière gauche passe à l'intérieur de l'écran et attaque l'intervalle.",
        "Tir de l'arrière gauche à 9 m ou passe au pivot qui se libère de l'écran.",
      ],
      en: [
        "CB passes to LB, the pivot sets the screen on the inside of defender 2.",
        "LB goes past the screen on the inside into the gap.",
        "Shot by LB from 9 m or pass to the pivot rolling off the screen.",
      ],
    }),
  };
}

function firstWave(): Template {
  const start = [
    tok("own", "tw", "TW", [0.8, 10]),
    tok("own", "la", "LA", [8, 18.4]),
    tok("own", "ra", "RA", [8, 1.6]),
    tok("own", "rm", "RM", [11, 10]),
    tok("opp", "o1", "1", [17, 12.5]),
    tok("opp", "o2", "2", [19, 6.5]),
    tok("opp", "otw", "TW", GOALKEEPER),
  ];
  const laEnd: P = [30, 17.6];
  const f1 = frame(start, {
    ball: { x: 0.8, y: 10 },
    arrows: [arrow("run", [8, 18.4], laEnd), arrow("run", [8, 1.6], [30, 2.4]), arrow("run", [11, 10], [22, 10]), arrow("pass", [0.8, 10], laEnd)],
  });
  const s2 = moved(start, { la: laEnd, ra: [30, 2.4], rm: [22, 10], o1: [32.6, 12.6], o2: [31, 7.4] });
  const shot: P = [35.4, 16.4];
  const f2 = frame(s2, { ball: { x: laEnd[0], y: laEnd[1] }, arrows: [arrow("run", laEnd, shot)] });
  const s3 = moved(s2, { la: shot, o1: [33.8, 13.8], rm: [26, 10] });
  const f3 = frame(s3, { ball: { x: shot[0], y: shot[1] }, duration_ms: 2500 });
  return {
    id: "fb_first_wave",
    category: "fast_break",
    formation: null,
    tags: ["Gegenstoss", "1. Welle"],
    ...doc(
      [f1, f2, f3],
      {
        "de-CH": [
          "Nach der Parade laufen beide Aussen sofort, der Torhüter spielt den langen Ball auf LA.",
          "LA fängt im Lauf vor der Mittellinie des Gegners, die Abwehr ist noch nicht formiert.",
          "Abschluss vom Flügel, bevor der zweite Verteidiger da ist; RM folgt als 2. Welle.",
        ],
        fr: [
          "Après l'arrêt, les deux ailiers partent tout de suite, le gardien joue long sur l'ailier gauche.",
          "L'ailier gauche reçoit en course, la défense n'est pas encore en place.",
          "Tir de l'aile avant le retour du deuxième défenseur ; le DC suit en 2e vague.",
        ],
        en: [
          "After the save both wings run at once, the goalkeeper plays the long ball to LW.",
          "LW catches on the run, the defence is not set yet.",
          "Finish from the wing before the second defender is back; CB follows as the second wave.",
        ],
      },
      "full",
    ),
  };
}

function freeThrow(): Template {
  const ball: P = [30.6, 10];
  const start = [
    tok("own", "rm", "RM", ball),
    tok("own", "rl", "RL", lineSpot(9.3, 0.2)),
    tok("own", "rr", "RR", lineSpot(9.3, -0.2)),
    tok("own", "km", "KM", lineSpot(9.4, 0.42)),
    tok("own", "la", "LA", [33.8, 19.2]),
    tok("own", "ra", "RA", [33.8, 0.8]),
    ...defence("6-0", "opp").map((t) => (["d3", "d4"].includes(t.id) ? { ...t, x: t.x + 0.4 } : t)),
  ];
  const rl = at(start, "rl");
  const rr = at(start, "rr");
  const blockL: P = [31.9, 11.7];
  const blockR: P = [31.9, 8.3];
  const f1 = frame(start, { ball: { x: ball[0], y: ball[1] }, arrows: [arrow("screen", rl, blockL), arrow("screen", rr, blockR)] });
  const s2 = moved(start, { rl: blockL, rr: blockR });
  const goal: P = [39.6, 11];
  const f2 = frame(s2, { ball: { x: ball[0], y: ball[1] }, arrows: [arrow("pass", ball, goal)] });
  const f3 = frame(s2, { ball: { x: goal[0], y: goal[1] }, duration_ms: 1500 });
  return {
    id: "sp_free_throw",
    category: "set_piece",
    formation: null,
    tags: ["Freiwurf", "9 m"],
    ...doc([f1, f2, f3], {
      "de-CH": [
        "Freiwurf an der 9-m-Linie: alle Angreifer ausserhalb der Linie, die Abwehr 3 m vom Ball.",
        "Mit dem Pfiff stellen RL und RR den Block vor 3 und 4, RM wirft durch die Lücke.",
        "Tor oder Abpraller: KM und die Aussen gehen nach.",
      ],
      fr: [
        "Jet franc sur la ligne des 9 m : tous les attaquants derrière la ligne, la défense à 3 m du ballon.",
        "Au coup de sifflet, les arrières gauche et droit font écran devant 3 et 4, le DC tire dans l'intervalle.",
        "But ou renvoi : le pivot et les ailiers suivent.",
      ],
      en: [
        "Free throw at the 9 m line: all attackers behind the line, the defence 3 m from the ball.",
        "On the whistle LB and RB block 3 and 4, CB shoots through the gap.",
        "Goal or rebound: the pivot and the wings follow up.",
      ],
    }),
  };
}

export const TEMPLATES: Template[] = [
  defenceTemplate("def_6_0", "6-0", "6:0", {
    "de-CH": "6:0: alle sechs Verteidiger einen Schritt vor der 6-m-Linie, verschieben zum Ball und helfen zur Mitte.",
    fr: "6-0 : les six défenseurs un pas devant la ligne des 6 m, ils coulissent côté ballon et aident vers le centre.",
    en: "6-0: all six defenders a step in front of the 6 m line, shifting to the ball and helping to the centre.",
  }),
  defenceTemplate("def_5_1", "5-1", "5:1", {
    "de-CH": "5:1: fünf an der 6-m-Linie, der vorgezogene Verteidiger 6 stört RM vor der 9-m-Linie.",
    fr: "5-1 : cinq sur la ligne des 6 m, l'avancé 6 gêne le demi-centre devant les 9 m.",
    en: "5-1: five at the 6 m line, the advanced defender 6 disrupts the centre back in front of 9 m.",
  }),
  defenceTemplate("def_3_2_1", "3-2-1", "3:2:1", {
    "de-CH": "3:2:1: drei an der 6-m-Linie, zwei Halbverteidiger auf 9 m, die Spitze 6 vor RM.",
    fr: "3-2-1 : trois sur la ligne des 6 m, deux demis à 9 m, la pointe 6 devant le demi-centre.",
    en: "3-2-1: three at the 6 m line, two half defenders at 9 m, the top defender 6 in front of the centre back.",
  }),
  defenceTemplate("def_4_2", "4-2", "4:2", {
    "de-CH": "4:2: vier an der 6-m-Linie, 5 und 6 nehmen RL und RR vor der 9-m-Linie heraus.",
    fr: "4-2 : quatre sur la ligne des 6 m, 5 et 6 sortent sur les arrières gauche et droit devant les 9 m.",
    en: "4-2: four at the 6 m line, 5 and 6 take out LB and RB in front of 9 m.",
  }),
  crossBack(),
  pivotScreen(),
  firstWave(),
  freeThrow(),
];

/** The template's play with the phase notes in the coach's language. */
export function templateDoc(tpl: Template, lang: string): PlayDoc {
  const l = (["de-CH", "fr", "en"].includes(lang) ? lang : "de-CH") as TemplateLang;
  return { ...tpl.doc, frames: tpl.doc.frames.map((f, i) => ({ ...f, note: tpl.notes[l][i] ?? f.note })) };
}

export function searchTemplates(query: string, category?: Template["category"]): Template[] {
  const q = query.trim().toLowerCase();
  return TEMPLATES.filter(
    (t) =>
      (!category || t.category === category) &&
      (!q || t.id.includes(q) || (t.formation ?? "").includes(q) || t.tags.some((g) => g.toLowerCase().includes(q))),
  );
}

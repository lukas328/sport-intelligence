/**
 * Two drills of the app's library (packages/tactics, as a copy in
 * apps/api/src/handball_api/services/drills.json), word for word, for the demo page's training
 * card: «6:0 Verschieben und Helfen» (Abwehr), which the coach picks for the right wing, and
 * «Rückzug 3 gegen 2 nach Ballverlust», the app's own training tip for goals after a fast break
 * (services/training_tips.py: topic transition_defence, basic drills first). drills.test.ts checks
 * that both are the same as in the library; change them together.
 */
import type { Locale } from "@/lib/i18n";

export type DrillLang = "de-CH" | "fr" | "en";
type Text = Record<DrillLang, string>;

export interface DrillToken {
  id: string;
  side: "own" | "opp";
  label: string;
  x: number;
  y: number;
}

export interface Drill {
  id: string;
  focus: string[];
  minutes: number;
  players: string;
  level: "basic" | "advanced";
  name: Text;
  setup: Text;
  procedure: Text;
  coaching: Text;
  variants: Text;
  sketch: {
    court: "half" | "full";
    tokens: DrillToken[];
    arrows: { kind: "pass" | "run" | "dribble"; points: [number, number][] }[];
    ball: { x: number; y: number } | null;
    cones: [number, number][];
  };
}

export const DRILL_LANG: Record<Locale, DrillLang> = { de: "de-CH", fr: "fr", en: "en" };

export const DRILLS: Record<"defence_6_0_shift" | "transition_3v2_back", Drill> = {
  defence_6_0_shift: {
    id: "defence_6_0_shift",
    focus: ["defence"],
    minutes: 15,
    players: "12",
    level: "basic",
    name: { "de-CH": "6:0 Verschieben und Helfen", fr: "6-0 coulisser et aider", en: "6-0 shifting and help" },
    setup: {
      "de-CH": "Angriff spielt den Ball schnell um den Kreis, Abwehr verschiebt ballorientiert und hilft zur Mitte.",
      fr: "L'attaque fait circuler vite, la défense coulisse côté ballon et aide vers le centre.",
      en: "The attack passes quickly around, the defence shifts to the ball and helps to the centre.",
    },
    procedure: {
      "de-CH": "Erst ohne Torwurf: der Verteidiger am Ball tritt heraus, die Nachbarn sichern nach innen. Danach darf der Angriff nach fünf Pässen werfen.",
      fr: "D'abord sans tir : le défenseur face au ballon sort, ses voisins couvrent vers l'intérieur. Ensuite l'attaque peut tirer après cinq passes.",
      en: "First without shots: the defender at the ball steps out, his neighbours cover inside. Then the attack may shoot after five passes.",
    },
    coaching: {
      "de-CH": "Kommunikation, Arme oben, Nebenmann sichert ab.",
      fr: "Communication, bras levés, le voisin couvre.",
      en: "Talk, arms up, the neighbour covers.",
    },
    variants: {
      "de-CH": "Mit Kreisläufer, der wandert; Angriff mit Kreuzen; Abwehr spielt aktiv mit Ballgewinn als Punkt.",
      fr: "Avec un pivot qui se déplace ; attaque avec croisés ; défense active, une interception vaut un point.",
      en: "With a pivot who moves; attack with crosses; active defence, winning the ball scores a point.",
    },
    sketch: {
      court: "half",
      tokens: [
        { id: "tw", side: "own", label: "TW", x: 39.3, y: 10 },
        { id: "d1", side: "own", label: "1", x: 37.85, y: 17.95 },
        { id: "d2", side: "own", label: "2", x: 34.62, y: 15.65 },
        { id: "d3", side: "own", label: "3", x: 33.21, y: 11.95 },
        { id: "d4", side: "own", label: "4", x: 33.21, y: 8.05 },
        { id: "d5", side: "own", label: "5", x: 34.62, y: 4.35 },
        { id: "d6", side: "own", label: "6", x: 37.85, y: 2.05 },
        { id: "la", side: "opp", label: "LA", x: 36.2, y: 19.2 },
        { id: "rl", side: "opp", label: "RL", x: 30.4, y: 16.45 },
        { id: "rm", side: "opp", label: "RM", x: 29, y: 10 },
        { id: "rr", side: "opp", label: "RR", x: 30.4, y: 3.55 },
        { id: "ra", side: "opp", label: "RA", x: 36.2, y: 0.8 },
        { id: "km", side: "opp", label: "KM", x: 33.7, y: 10 },
      ],
      arrows: [
        { kind: "pass", points: [[29, 10], [30.4, 16.45]] },
        { kind: "run", points: [[34.62, 15.65], [32.87, 15.93]] },
        { kind: "run", points: [[33.21, 11.95], [33.54, 13.62]] },
        { kind: "run", points: [[33.21, 8.05], [33.2, 10.49]] },
      ],
      ball: { x: 29, y: 10 },
      cones: [],
    },
  },
  transition_3v2_back: {
    id: "transition_3v2_back",
    focus: ["transition_defence"],
    minutes: 12,
    players: "6-12",
    level: "basic",
    name: { "de-CH": "Rückzug 3 gegen 2 nach Ballverlust", fr: "Repli à 3 contre 2 après la perte", en: "Getting back 3 against 2 after a turnover" },
    setup: {
      "de-CH": "Ganzes Feld. Drei Angreifer an der Mittellinie mit Ball, zwei Verteidiger einen Schritt weiter vorne, Torhüter.",
      fr: "Terrain entier. Trois attaquants à la ligne médiane avec ballon, deux défenseurs un pas plus loin, gardien.",
      en: "Full court. Three attackers at the centre line with the ball, two defenders a step further up, goalkeeper.",
    },
    procedure: {
      "de-CH": "Auf Pfiff greifen die drei an, die zwei sprinten zurück und verteidigen in Unterzahl bis zum Abschluss.",
      fr: "Au coup de sifflet, les trois attaquent, les deux reviennent en sprint et défendent en infériorité jusqu'au tir.",
      en: "On the whistle the three attack, the two sprint back and defend outnumbered until the shot.",
    },
    coaching: {
      "de-CH": "Zuerst die Mitte und den Ball sichern, Zeit gewinnen, bis Hilfe kommt; nicht zu früh herausgehen.",
      fr: "D'abord protéger l'axe et le ballon, gagner du temps jusqu'au retour des autres ; ne pas sortir trop tôt.",
      en: "Protect the middle and the ball first, win time until help arrives; do not step out too early.",
    },
    variants: {
      "de-CH": "Dritter Verteidiger startet zwei Sekunden später; Angreifer müssen in acht Sekunden abschliessen.",
      fr: "Un troisième défenseur part deux secondes plus tard ; les attaquants doivent finir en huit secondes.",
      en: "A third defender starts two seconds later; attackers must finish within eight seconds.",
    },
    sketch: {
      court: "full",
      tokens: [
        { id: "tw", side: "own", label: "TW", x: 0.7, y: 10 },
        { id: "a1", side: "own", label: "1", x: 23.4, y: 13 },
        { id: "a2", side: "own", label: "2", x: 24.6, y: 7 },
        { id: "d1", side: "opp", label: "1", x: 20.6, y: 16.4 },
        { id: "d2", side: "opp", label: "2", x: 20.2, y: 10 },
        { id: "d3", side: "opp", label: "3", x: 20.6, y: 3.6 },
      ],
      arrows: [
        { kind: "run", points: [[23.4, 13], [8.4, 12]] },
        { kind: "run", points: [[24.6, 7], [8.8, 7.8]] },
        { kind: "dribble", points: [[20.2, 10], [11.6, 10]] },
        { kind: "run", points: [[20.6, 16.4], [12.6, 16.2]] },
        { kind: "run", points: [[20.6, 3.6], [12.6, 3.8]] },
      ],
      ball: { x: 20.2, y: 10 },
      cones: [],
    },
  },
};

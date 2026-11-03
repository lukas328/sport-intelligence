/**
 * Drill library (BRIEF 4.10 "Trainingsübungen", M7). Common handball exercises with a focus, linked to the
 * insight rules: an insight about weak wing shots suggests the wing finishing drills. Texts in de-CH, en, fr.
 */

export type Focus =
  | "finishing"
  | "wings"
  | "back_court"
  | "pivot"
  | "seven_m"
  | "goalkeeping"
  | "passing"
  | "transition_defence"
  | "fast_break"
  | "defence"
  | "powerplay";

export type Lang = "de-CH" | "en" | "fr";
type Text = Record<Lang, string>;

export interface Drill {
  id: string;
  focus: Focus[];
  minutes: number;
  players: string; // e.g. "6-12"
  level: "basic" | "advanced";
  name: Text;
  setup: Text;
  coaching: Text;
}

export const DRILLS: Drill[] = [
  {
    id: "finishing_wings",
    focus: ["finishing", "wings"],
    minutes: 15,
    players: "6-12",
    level: "basic",
    name: { "de-CH": "Flügelwürfe unter Druck", en: "Wing shots under pressure", fr: "Tirs à l'aile sous pression" },
    setup: {
      "de-CH": "Zwei Kolonnen auf den Flügeln, Zuspiel aus dem Rückraum, ein passiver Verteidiger engt den Winkel ein.",
      en: "Two lines on the wings, pass from the back court, one passive defender narrows the angle.",
      fr: "Deux colonnes aux ailes, passe depuis la base arrière, un défenseur passif réduit l'angle.",
    },
    coaching: {
      "de-CH": "Absprung möglichst nah an der Seitenlinie, Wurfbild variieren (kurze und lange Ecke).",
      en: "Take off close to the side line, vary the target (near and far corner).",
      fr: "Appel près de la ligne de touche, varier la cible (premier et second poteau).",
    },
  },
  {
    id: "finishing_back",
    focus: ["finishing", "back_court"],
    minutes: 15,
    players: "6-12",
    level: "basic",
    name: { "de-CH": "Rückraumwurf aus dem Lauf", en: "Back court shot on the run", fr: "Tir de la base arrière en course" },
    setup: {
      "de-CH": "Drei Rückraumpositionen, Stossbewegung auf die Lücke, Sprungwurf über einen Blockspieler.",
      en: "Three back court positions, attack the gap, jump shot over a blocking defender.",
      fr: "Trois postes arrière, attaque de l'intervalle, tir en suspension au-dessus d'un contreur.",
    },
    coaching: {
      "de-CH": "Wurfarm früh oben, Wurf am höchsten Punkt, nicht immer in die gleiche Ecke.",
      en: "Throwing arm up early, release at the highest point, do not always pick the same corner.",
      fr: "Bras armé tôt, lâcher au point le plus haut, varier les angles.",
    },
  },
  {
    id: "finishing_pivot",
    focus: ["finishing", "pivot"],
    minutes: 12,
    players: "4-8",
    level: "basic",
    name: { "de-CH": "Kreisanspiel und Abschluss", en: "Pivot pass and finish", fr: "Passe au pivot et finition" },
    setup: {
      "de-CH": "Kreisläufer sperrt gegen einen Verteidiger, Rückraum spielt in den Lauf, Abschluss mit Fallwurf.",
      en: "Pivot screens a defender, back court passes into the run, finish with a falling shot.",
      fr: "Le pivot fait écran, la base arrière passe dans la course, finition en tir en chute.",
    },
    coaching: {
      "de-CH": "Sicher fangen vor dem Drehen, Torhüter mit Täuschung bewegen.",
      en: "Secure the catch before turning, move the goalkeeper with a feint.",
      fr: "Sécuriser la réception avant de pivoter, faire bouger le gardien par une feinte.",
    },
  },
  {
    id: "seven_m_routine",
    focus: ["seven_m"],
    minutes: 10,
    players: "2-6",
    level: "basic",
    name: { "de-CH": "7-m-Routine mit Druck", en: "Penalty routine under pressure", fr: "Routine de 7 m sous pression" },
    setup: {
      "de-CH": "Jeder Werfer hat eine feste Routine, nach einem Sprint direkt an die Linie, Serie von fünf Würfen.",
      en: "Each shooter has a fixed routine, straight to the line after a sprint, series of five shots.",
      fr: "Chaque tireur a une routine fixe, directement à la ligne après un sprint, série de cinq tirs.",
    },
    coaching: {
      "de-CH": "Ziel vor dem Pfiff festlegen, ruhiger Atem, Torhüter nicht anschauen.",
      en: "Decide the target before the whistle, calm breathing, do not watch the goalkeeper.",
      fr: "Choisir la cible avant le coup de sifflet, respiration calme, ne pas regarder le gardien.",
    },
  },
  {
    id: "keeper_reaction",
    focus: ["goalkeeping"],
    minutes: 15,
    players: "1-6",
    level: "basic",
    name: { "de-CH": "Torhüter: Reaktion und Stellung", en: "Goalkeeper: reaction and position", fr: "Gardien : réaction et placement" },
    setup: {
      "de-CH": "Würfe aus wechselnden Positionen in schneller Folge, Fokus auf die Zone mit den meisten Gegentoren.",
      en: "Shots from changing positions in quick succession, focus on the zone with most goals against.",
      fr: "Tirs de positions variées en succession rapide, priorité à la zone la plus touchée.",
    },
    coaching: {
      "de-CH": "Grundstellung auf der Winkelhalbierenden, Arme und Beine gleichzeitig, schnell zurück in die Mitte.",
      en: "Base position on the bisector, arms and legs together, quickly back to the centre.",
      fr: "Position de base sur la bissectrice, bras et jambes ensemble, retour rapide au centre.",
    },
  },
  {
    id: "keeper_wings",
    focus: ["goalkeeping", "wings"],
    minutes: 12,
    players: "3-8",
    level: "advanced",
    name: { "de-CH": "Torhüter gegen Flügelwürfe", en: "Goalkeeper against wing shots", fr: "Gardien contre tirs à l'aile" },
    setup: {
      "de-CH": "Flügelspieler werfen aus spitzem Winkel, Torhüter übt das Abdecken der kurzen Ecke und das Nachrücken.",
      en: "Wings shoot from a narrow angle, the goalkeeper practises covering the near post and stepping out.",
      fr: "Les ailiers tirent avec un angle fermé, le gardien travaille le premier poteau et la sortie.",
    },
    coaching: {
      "de-CH": "Kurzen Pfosten zu, Schritt dem Werfer entgegen, spät reagieren.",
      en: "Close the near post, step towards the shooter, react late.",
      fr: "Fermer le premier poteau, avancer vers le tireur, réagir tard.",
    },
  },
  {
    id: "passing_pressure",
    focus: ["passing"],
    minutes: 12,
    players: "8-14",
    level: "basic",
    name: { "de-CH": "Passspiel gegen offensive Abwehr", en: "Passing against an aggressive defence", fr: "Passes contre une défense agressive" },
    setup: {
      "de-CH": "4 gegen 2 im Feld 15 x 15 m, maximal drei Sekunden Ballbesitz, Fehlpässe zählen als Punkt für die Abwehr.",
      en: "4 against 2 in a 15 x 15 m area, at most three seconds on the ball, bad passes score for the defence.",
      fr: "4 contre 2 sur 15 x 15 m, trois secondes maximum avec le ballon, une mauvaise passe donne un point à la défense.",
    },
    coaching: {
      "de-CH": "Freilaufen vor dem Pass, Blickkontakt, Pass in die Laufrichtung.",
      en: "Get open before the pass, eye contact, pass into the running direction.",
      fr: "Se démarquer avant la passe, contact visuel, passe dans la course.",
    },
  },
  {
    id: "transition_back",
    focus: ["transition_defence"],
    minutes: 15,
    players: "10-14",
    level: "advanced",
    name: { "de-CH": "Schnelles Rückzugsverhalten", en: "Fast transition back", fr: "Repli défensif rapide" },
    setup: {
      "de-CH": "Angriff 6 gegen 6, nach Abschluss oder Ballverlust sofort Gegenstoss des Gegners; Rückzug im Sprint.",
      en: "Attack 6 against 6, after a shot or turnover the opponent counters at once; sprint back.",
      fr: "Attaque 6 contre 6, après tir ou perte de balle contre-attaque immédiate ; repli en sprint.",
    },
    coaching: {
      "de-CH": "Der Spieler nach dem Ballverlust stört den ersten Pass, alle anderen zuerst zum eigenen 9 m.",
      en: "The player who lost the ball disrupts the first pass, everybody else back to their own 9 m first.",
      fr: "Le joueur qui perd le ballon gêne la première passe, les autres reviennent d'abord aux 9 m.",
    },
  },
  {
    id: "fast_break_waves",
    focus: ["fast_break"],
    minutes: 15,
    players: "8-14",
    level: "basic",
    name: { "de-CH": "Gegenstoss in drei Wellen", en: "Fast break in three waves", fr: "Contre-attaque en trois vagues" },
    setup: {
      "de-CH": "Nach Parade langer Pass auf die Flügel (1. Welle), Rückraum folgt (2. Welle), Kreis zuletzt.",
      en: "After a save a long pass to the wings (first wave), back court follows (second wave), pivot last.",
      fr: "Après un arrêt longue passe aux ailiers (1re vague), la base arrière suit (2e vague), le pivot en dernier.",
    },
    coaching: {
      "de-CH": "Flügel starten beim Wurf des Gegners, Torhüter schaut zuerst lang.",
      en: "Wings start when the opponent shoots, goalkeeper looks long first.",
      fr: "Les ailiers partent au tir adverse, le gardien regarde d'abord loin.",
    },
  },
  {
    id: "defence_6_0_shift",
    focus: ["defence"],
    minutes: 15,
    players: "12",
    level: "basic",
    name: { "de-CH": "6:0 Verschieben und Helfen", en: "6-0 shifting and help", fr: "6-0 coulisser et aider" },
    setup: {
      "de-CH": "Angriff spielt den Ball schnell um den Kreis, Abwehr verschiebt ballorientiert und hilft zur Mitte.",
      en: "The attack passes quickly around, the defence shifts to the ball and helps to the centre.",
      fr: "L'attaque fait circuler vite, la défense coulisse côté ballon et aide vers le centre.",
    },
    coaching: {
      "de-CH": "Kommunikation, Arme oben, Nebenmann sichert ab.",
      en: "Talk, arms up, the neighbour covers.",
      fr: "Communication, bras levés, le voisin couvre.",
    },
  },
  {
    id: "powerplay_7v6",
    focus: ["powerplay"],
    minutes: 12,
    players: "13",
    level: "advanced",
    name: { "de-CH": "Überzahl 6 gegen 5", en: "Powerplay 6 against 5", fr: "Supériorité 6 contre 5" },
    setup: {
      "de-CH": "Angriff in Überzahl mit zwei Kreisläufern, Ziel: freier Wurf aus der Nahdistanz innert 30 Sekunden.",
      en: "Attack in powerplay with two pivots, aim: a free close-range shot within 30 seconds.",
      fr: "Attaque en supériorité avec deux pivots, objectif : tir libre de près en 30 secondes.",
    },
    coaching: {
      "de-CH": "Ball schnell bewegen, Überzahl auf einer Seite schaffen, Geduld bis zur klaren Chance.",
      en: "Move the ball fast, create the extra player on one side, be patient until the clear chance.",
      fr: "Faire circuler vite, créer le surnombre d'un côté, patience jusqu'à l'occasion nette.",
    },
  },
];

/** Focus areas suggested by an insight (key from handball_metrics.insights, zone from its params). */
export function focusForInsight(key: string, zone?: string | null): Focus[] {
  const rule = key.replace("insights.", "");
  if (rule.startsWith("zone_")) {
    if (zone?.startsWith("wing")) return ["wings"];
    if (zone?.startsWith("back") || zone?.startsWith("half")) return ["back_court"];
    if (zone?.startsWith("circle")) return ["pivot"];
    return ["finishing"];
  }
  const map: Record<string, Focus[]> = {
    shooting_below: ["finishing"],
    drought: ["finishing"],
    seven_m_low: ["seven_m"],
    saves_below: ["goalkeeping"],
    keeper_bad: ["goalkeeping"],
    conceded_zone: ["goalkeeping"],
    turnovers_high: ["passing"],
    fast_breaks_against: ["transition_defence"],
    powerplay_weak: ["powerplay"],
    player_inefficient: ["finishing"],
  };
  return map[rule] ?? [];
}

export function drillsFor(focus: Focus[]): Drill[] {
  return DRILLS.filter((d) => d.focus.some((f) => focus.includes(f)));
}

/**
 * Words of a search sentence as the chips of the scene search (SPEC 7.6, UX test B02, B19):
 * «Wie viele Gegentore über rechts aussen in den letzten drei Spielen?» becomes conceded,
 * wing_right, last_3. Plain word matching in de, fr and en; what is not understood stays text.
 */
const RULES: { chip: string; words: RegExp }[] = [
  { chip: "conceded", words: /\b(gegentor\w*|buts? encaiss\w*|encaiss\w*|goals? (conceded|against)|conceded)\b/ },
  { chip: "saves", words: /\b(parade\w*|gehalten\w*|arr[eê]ts?|saves?)\b/ },
  { chip: "turnovers", words: /\b(ballverlust\w*|fehlp[aä]ss\w*|pertes? de balle|turnovers?)\b/ },
  { chip: "scored", words: /\b(eigene tore|unsere tore|tore|tor|buts?|goals?)\b/ },
  { chip: "wing_right", words: /\b(rechts ?aussen|rechtsaussen|rechter? fl[uü]gel|ailier droit|aile droite|right wing)\b/ },
  { chip: "wing_left", words: /\b(links ?aussen|linksaussen|linker? fl[uü]gel|ailier gauche|aile gauche|left wing)\b/ },
  { chip: "back_left", words: /\b(r[uü]ckraum links|arri[eè]re gauche|left back)\b/ },
  { chip: "back_centre", words: /\b(r[uü]ckraum mitte|demi-centre|centre back)\b/ },
  { chip: "back_right", words: /\b(r[uü]ckraum rechts|arri[eè]re droit|right back)\b/ },
  { chip: "circle", words: /\b(kreis\w*|pivot|circle|line player)\b/ },
  { chip: "last_3", words: /\b(letzten? (drei|3) spiel\w*|trois derniers matchs|3 derniers matchs|last (three|3) (matches|games))\b/ },
  { chip: "last_match", words: /\b(letzte[sn]? spiel|dernier match|last (match|game))\b/ },
];

const GROUP: Record<string, string> = {
  conceded: "event",
  scored: "event",
  saves: "event",
  turnovers: "event",
  wing_right: "position",
  wing_left: "position",
  back_left: "position",
  back_centre: "position",
  back_right: "position",
  circle: "position",
  last_3: "range",
  last_match: "range",
};

/** The chips a sentence names, one per group, the first rule of a group wins. */
export function chipsFromText(text: string): string[] {
  const s = ` ${text.toLowerCase().replace(/[?!.,;:«»"]/g, " ").replace(/\s+/g, " ")} `;
  const out: string[] = [];
  const taken = new Set<string>();
  for (const r of RULES) {
    const g = GROUP[r.chip]!;
    if (taken.has(g) || !r.words.test(s)) continue;
    out.push(r.chip);
    taken.add(g);
  }
  return out;
}

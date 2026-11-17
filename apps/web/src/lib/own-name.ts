/**
 * The name of our side in heads, telegram and camera (UX test H11): the team's own name when it
 * is one («SG Lärchenwil/Kalvenegg», a joint team), else the club's («HC Tannengrün» for «Herren 1»).
 */
const GENERIC = /^(herren|damen|männer|frauen|junior(en|innen)?|mixed|u\s?\d+|[a-e]-junior|hommes|femmes|men|women)\b/i;

export function ownName(team: string | null | undefined, club: string): string {
  const t = team?.trim();
  return t && !GENERIC.test(t) ? t : club;
}

/** A team name for the narrow phone bar: additions in brackets dropped, breaks after «/» and «-». */
export function headName(name: string): string {
  return name
    .replace(/\s*\([^)]*\)/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/([/-])(?=\S)/g, "$1\u200b");
}

const fold = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

/**
 * The club's name in the frame only when it says more than the team's (finding K7): \u00abTV Farnwil\u00bb
 * and the team \u00abTV Farnwil\u00bb show the name once; a team \u00abTV Farnwil 2\u00bb already carries the club.
 * Null: leave the club's name out (the crest and the team stay).
 */
export function clubNameShown(club: string, team: string | null | undefined): string | null {
  const c = fold(club);
  const t = fold(team ?? "");
  if (!t || !c) return club;
  return ` ${t} `.includes(` ${c} `) ? null : club;
}

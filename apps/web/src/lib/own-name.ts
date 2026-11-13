/**
 * The name of our side in heads, telegram and camera (UX test H11): the team's own name when it
 * is one («SG Wädenswil/Horgen», a joint team), else the club's («HC Zürichsee» for «Herren 1»).
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

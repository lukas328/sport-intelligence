/**
 * A team made by hand can exist twice in a club (finding K17: the official data allow each team
 * once, a name typed by hand does not). Before making one, the club's teams with a similar name
 * are shown: the same words, ignoring case, accents, punctuation and a trailing «1».
 */

function words(name: string): string[] {
  return name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    // «U-17» and «U17» are one word
    .replace(/\b([a-z])[^a-z0-9]+(\d)/g, "$1$2")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(" ")
    .filter((w) => w && w !== "1" && w !== "i");
}

export function similarTeams<T extends { name: string }>(name: string, teams: T[]): T[] {
  const want = words(name);
  if (want.length === 0) return [];
  const key = want.join(" ");
  return teams.filter((x) => {
    const have = words(x.name);
    const other = have.join(" ");
    if (other === key) return true;
    // one name is the other with more words («Herren» and «Herren 2» are not the same team, but
    // «TV Farnwil Herren» and «Herren» likely are)
    const [short, long] = want.length <= have.length ? [want, have] : [have, want];
    const extra = long.filter((w) => !short.includes(w));
    return short.every((w) => long.includes(w)) && extra.every((w) => !/^\d+$/.test(w)) && short.length > 0 && extra.length <= 2;
  });
}

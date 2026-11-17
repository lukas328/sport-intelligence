/**
 * A league table from handball.ch, the same on Start, Spiele and Saison (livegang K1): first an
 * excerpt around the own team (and the next opponent, where one is marked), the whole table one
 * tap away.
 */
export interface TableRow {
  key: string;
  rank: number | null;
  name: string;
  games: number | null;
  diff: number | null;
  points: number | null;
  /** the coach's own team */
  own?: boolean;
  /** another team worth seeing in the excerpt (the next opponent) */
  marked?: boolean;
}

/** The rows of the excerpt: about `size` rows around the own and marked teams, in table order.
 * Without either, the top of the table. A table barely longer than the excerpt is shown whole. */
export function tableExcerpt(rows: TableRow[], size = 5): TableRow[] {
  if (rows.length <= size + 1) return rows;
  const hits = rows.flatMap((r, i) => (r.own || r.marked ? [i] : []));
  if (hits.length === 0) return rows.slice(0, size);
  if (hits.length === 1) {
    const start = Math.min(Math.max(0, hits[0]! - Math.floor(size / 2)), rows.length - size);
    return rows.slice(start, start + size);
  }
  // several teams: each with its neighbours above and below
  const keep = new Set<number>();
  for (const i of hits) for (let j = i - 1; j <= i + 1; j++) if (j >= 0 && j < rows.length) keep.add(j);
  return [...keep].sort((a, b) => a - b).map((i) => rows[i]!);
}

/** «+3», «-2», «0»: the goal difference as tables write it. */
export function signed(v: number | null | undefined): string {
  if (v == null) return "";
  return v > 0 ? `+${v}` : String(v);
}

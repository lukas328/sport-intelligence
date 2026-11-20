/**
 * The goal moment behind a question of the round in Prüfen. The round's list is taken once when
 * the screen opens, so answering does not shuffle the count. A moment answered in this round
 * stays in it: otherwise the refetched candidates (no longer «open») took it out of the list and
 * «Frage 4 von 5» jumped to «Frage 3 von 4» (e2e 20.11., real-normal.spec under load). A moment
 * answered elsewhere (another device, the report) drops out.
 */
export function roundCandidate<C extends { id: string; status: string }>(candidates: readonly C[] | undefined, id: string, answeredHere: ReadonlySet<string> | readonly string[]): C | undefined {
  const here = Array.isArray(answeredHere) ? answeredHere.includes(id) : (answeredHere as ReadonlySet<string>).has(id);
  return candidates?.find((x) => x.id === id && (x.status === "open" || here));
}

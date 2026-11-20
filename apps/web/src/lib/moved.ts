/**
 * Old app addresses that always lead to the same new one, answered by the middleware with a real
 * redirect (307) before anything renders.
 *
 * Why not `redirect()` in the page: the pages sit under a `loading.tsx`, so the frame is already
 * streaming when the page redirects. Next then answers 200 with `<meta http-equiv="refresh"
 * content="1;url=…">` and redirects on the client. The meta element stays in the document: one
 * second later the browser loads the new address a second time (a full reload), and every client
 * navigation from that page becomes a full page load. In the e2e run this destroyed the page under
 * a running check («execution context destroyed» after «Suchen» in data.spec, e2e 20.11.).
 * The pages keep their `redirect()` as a fallback.
 */
export function movedAddress(pathname: string, search: URLSearchParams): string | null {
  const team = pathname.match(/^(\/app\/[^/]+\/teams\/[^/]+)\/(assistant|search|library|paper|matrix)\/?$/);
  if (team) {
    const [, base, old] = team;
    if (old === "assistant") {
      const q = search.get("q");
      return `${base}/scenes${q ? `?q=${encodeURIComponent(q)}` : "?focus=1"}`;
    }
    if (old === "search") return `${base}/scenes${search.size ? `?${search}` : ""}`;
    if (old === "library") return `${base}/collections`;
    if (old === "paper") return `${base}/matches`;
    // the pivot itself stays reachable with ?pivot=1
    return search.get("pivot") === "1" ? null : `${base}/scenes?view=table`;
  }
  const match = pathname.match(/^(\/app\/[^/]+\/matches\/[^/]+)\/(marks|live)\/?$/);
  if (match) return `${match[1]}/matchday?mode=${match[2] === "marks" ? "marks" : "detail"}`;
  const org = pathname.match(/^(\/app\/[^/]+)\/(profile|settings\/access-requests)\/?$/);
  if (org) return org[2] === "profile" ? `${org[1]}/me` : `${org[1]}/club/federation`;
  return null;
}

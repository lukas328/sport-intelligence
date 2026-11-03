/**
 * Deep links of the native app (addendum 01, 5.5): handball://clip/<match>?t=<ms>, and web links
 * from push notifications and e-mails (/app/<org>/matches/<id>?t=..., /app/<org>/assignments ...).
 */
export type Route =
  | { screen: "clip"; matchId: string; t: number }
  | { screen: "match"; orgId: string; matchId: string; t: number }
  | { screen: "assignments"; orgId: string }
  | { screen: "feed"; orgId: string }
  | { screen: "schedule"; orgId: string }
  | { screen: "presentation"; orgId: string; presentationId: string }
  | { screen: "home" };

const UUID = "[0-9a-fA-F-]{36}";

function time(params: URLSearchParams): number {
  const t = Number(params.get("t") ?? 0);
  return Number.isFinite(t) && t > 0 ? Math.round(t) : 0;
}

export function parse(link: string | null | undefined): Route {
  if (!link) return { screen: "home" };
  let url: URL;
  try {
    url = new URL(link, "https://app.invalid");
  } catch {
    return { screen: "home" };
  }
  const path = url.protocol === "handball:" ? `/${url.host}${url.pathname}` : url.pathname;
  let m = path.match(new RegExp(`^/clip/(${UUID})/?$`));
  if (m) return { screen: "clip", matchId: m[1]!, t: time(url.searchParams) };
  m = path.match(new RegExp(`^/app/(${UUID})/matches/(${UUID})/?$`));
  if (m) return { screen: "match", orgId: m[1]!, matchId: m[2]!, t: time(url.searchParams) };
  m = path.match(new RegExp(`^/app/(${UUID})/(assignments|feed|schedule)/?`));
  if (m) return { screen: m[2] as "assignments" | "feed" | "schedule", orgId: m[1]! };
  m = path.match(new RegExp(`^/app/(${UUID})/presentations/(${UUID})`));
  if (m) return { screen: "presentation", orgId: m[1]!, presentationId: m[2]! };
  return { screen: "home" };
}

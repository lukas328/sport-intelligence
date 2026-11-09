import type { Route } from "@handball/client-core";

/** App path for a deep link route (5.5). */
export function pathFor(r: Route): string {
  switch (r.screen) {
    case "clip":
      return `/clip/${r.matchId}?t=${r.t}`;
    case "match":
      return `/clip/${r.matchId}?t=${r.t}`;
    case "assignments":
      return "/assignments";
    case "feed":
      return "/feed";
    case "schedule":
      return "/schedule";
    case "presentation":
      return `/remote/${r.presentationId}${r.key ? `?key=${encodeURIComponent(r.key)}` : ""}`;
    default:
      return "/feed";
  }
}

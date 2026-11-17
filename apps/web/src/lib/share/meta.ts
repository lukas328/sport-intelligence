import type { Schemas } from "@handball/api-client";
import type { Metadata } from "next";
import { shareUrl, type T } from "./text";

/**
 * Open Graph and Twitter tags of a shared page (K20, R2): a title that says what one sees and
 * makes curious («Szene 24. Min: Tor über aussen links»), one line of description, the club as
 * site name, a 1200 x 630 picture (absolute URL), and for a highlight reel the MP4 itself
 * (iMessage plays it in the chat). No names of people anywhere.
 */

export type SharePreview = Schemas["SharePreview"];

/** Bump when the preview picture changes: chats cache a picture per URL. */
export const OG_VERSION = 2;
export const OG_SIZE = { width: 1200, height: 630 } as const;
const BRAND = "Handball Intelligence";
const DESCRIPTION_MAX = 90;

const scoreOf = (s: readonly number[] | null | undefined) => (s && s.length === 2 ? `${s[0]}:${s[1]}` : null);

/** The match minute of a clock in minutes: 22:58 is the 23rd minute (handball counts on). */
export function matchMinute(minute: number | null | undefined): number | null {
  if (minute == null || minute < 0) return null;
  return Math.floor(minute) + 1;
}

/** «Tor von aussen links», «Gegentor nach Gegenstoss»: one goal, said as one (second round Q2). */
export function goalWords(t: T, goal: { team: "own" | "opp"; zone: string | null }): string {
  const zone = goal.zone ? t(`collections.sceneZone.${goal.zone}`) : "";
  return t(goal.team === "opp" ? "share.og.goalAgainst" : "share.og.goalFor", { zone }).trim();
}

function teamLine(p: Pick<SharePreview, "club" | "team">): string {
  return p.club && p.club !== p.team && !p.team.startsWith(p.club) ? `${p.club} ${p.team}` : p.team || p.club;
}

/** The title in the chat: what it is and the one concrete thing (minute, result, count). */
export function ogTitle(t: T, p: SharePreview): string {
  const score = scoreOf(p.score);
  const team = teamLine(p);
  switch (p.kind) {
    case "scene": {
      const minute = matchMinute(p.goal?.minute);
      if (p.goal && minute != null) return t("share.og.sceneMinute", { minute, what: goalWords(t, p.goal) });
      if (p.goal) return t("share.og.scene", { title: goalWords(t, p.goal) });
      return p.opponent && (!p.title || p.title.includes(" - ")) ? t("share.og.sceneVs", { opponent: p.opponent }) : t("share.og.scene", { title: p.title });
    }
    case "collection":
    case "playlist":
      return p.scenes ? t("share.og.run", { title: p.title, n: p.scenes }) : p.title;
    case "match":
      if (p.opponent && score) return t("share.og.matchScore", { team, score, opponent: p.opponent });
      return p.opponent ? t("share.og.matchVs", { team, opponent: p.opponent }) : p.title;
    case "highlight":
      if (p.opponent && score) return t("share.og.highlightScore", { team, score, opponent: p.opponent });
      return t("share.og.highlight", { team });
    case "play":
      return t("share.og.play", { title: p.title });
    default:
      return p.title;
  }
}

function minutesOf(s: number | null | undefined): number | null {
  return s ? Math.max(1, Math.round(s / 60)) : null;
}

/** One line under the title: team, date or length, «ohne Konto ansehen». */
export function ogDescription(t: T, p: SharePreview, locale = "de-CH"): string {
  const parts: string[] = [teamLine(p)];
  if (p.kind === "match" || p.kind === "highlight") {
    if (p.kickoff_at) parts.push(new Intl.DateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric", timeZone: "Europe/Zurich" }).format(new Date(p.kickoff_at)));
    if (p.halftime && p.halftime.length === 2) parts.push(t("share.og.halftime", { score: `${p.halftime[0]}:${p.halftime[1]}` }));
  } else if (p.kind === "scene") {
    if (p.opponent) parts.push(t("share.og.vs", { opponent: p.opponent }));
  } else if (p.kind === "collection" || p.kind === "playlist") {
    const m = minutesOf(p.duration_s);
    if (m) parts.push(t("share.previewMinutes", { n: m }));
  } else if (p.kind === "play" && p.play) {
    const phases = (p.play.doc as { frames?: unknown[] }).frames?.length ?? 0;
    if (phases > 1) parts.push(t("share.og.phases", { n: phases }));
  }
  parts.push(t("share.og.noAccount"));
  const line = parts.filter(Boolean).join(" · ");
  return line.length > DESCRIPTION_MAX ? `${line.slice(0, DESCRIPTION_MAX - 1).trimEnd()}…` : line;
}

/** The text of the picture for screen readers and chats that show it. */
export function ogAlt(t: T, p: SharePreview): string {
  return t("share.og.alt", { title: ogTitle(t, p), team: teamLine(p) });
}

/** The URL of the reel for og:video (direct MP4, so iMessage plays it inline). */
export function reelUrl(origin: string, token: string): string {
  return `${origin.replace(/\/$/, "")}/v1/share/${token}/reel.mp4`;
}

export function ogImageUrl(origin: string, token: string): string {
  return `${shareUrl(origin, token)}/og?v=${OG_VERSION}`;
}

/** Next.js metadata of a shared page. */
export function shareMetadata(t: T, p: SharePreview, opts: { origin: string; token: string; locale?: string }): Metadata {
  const title = ogTitle(t, p);
  const description = ogDescription(t, p, opts.locale);
  const url = shareUrl(opts.origin, opts.token);
  const image = { url: ogImageUrl(opts.origin, opts.token), width: OG_SIZE.width, height: OG_SIZE.height, alt: ogAlt(t, p), type: "image/png" };
  const portrait = p.reel?.format === "9x16";
  const videos = p.kind === "highlight" && p.reel ? [{ url: reelUrl(opts.origin, opts.token), secureUrl: reelUrl(opts.origin, opts.token), type: "video/mp4", width: portrait ? 1080 : 1920, height: portrait ? 1920 : 1080 }] : undefined;
  return {
    title: { absolute: title },
    description,
    robots: { index: false, follow: false },
    alternates: { canonical: url },
    openGraph: {
      type: videos ? "video.other" : "website",
      url,
      title,
      description,
      siteName: p.club || BRAND,
      locale: (opts.locale ?? "de-CH").replace("-", "_"),
      images: [image],
      ...(videos ? { videos } : {}),
    },
    twitter: { card: "summary_large_image", title, description, images: [image] },
  };
}

/**
 * The public origin of the app for absolute URLs in the tags: the configured base URL, else the
 * host the request came in on (behind the Azure ingress: x-forwarded-host and -proto).
 */
export function publicOrigin(h: { get(name: string): string | null }, configured?: string | null): string {
  if (configured) return configured.replace(/\/$/, "");
  const host = h.get("x-forwarded-host")?.split(",")[0]?.trim() || h.get("host") || "localhost:3000";
  const local = /^(localhost|127\.|\[::1\])/.test(host);
  const proto = h.get("x-forwarded-proto")?.split(",")[0]?.trim() || (local ? "http" : "https");
  return `${proto}://${host}`;
}

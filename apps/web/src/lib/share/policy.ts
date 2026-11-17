import type { ShareKind } from "./text";

/**
 * Who may share what publicly (K18, K20), as the API answers it (`share-options`) or refuses it.
 * The rules live in the API (`services/sharing.py`); the app only explains them:
 * youth teams share plays only (youth protection), highlights need the consent «Highlights
 * öffentlich» of everybody shown, a club claimed from the official data shares after it is
 * confirmed, and the plan must include share links.
 */
export type ShareReason = "forbidden" | "plan" | "unverified" | "youth-protection" | "consent-missing";

export interface ShareOptions {
  youth: boolean;
  default_days: number;
  kinds: Record<string, string | null | undefined>;
}

const REASONS: readonly ShareReason[] = ["forbidden", "plan", "unverified", "youth-protection", "consent-missing"];

/** Why this kind cannot be shared here, or null. Unknown options: allowed (the API decides). */
export function blockedReason(options: ShareOptions | null | undefined, kind: ShareKind): ShareReason | null {
  const r = options?.kinds[kind];
  return r && (REASONS as readonly string[]).includes(r) ? (r as ShareReason) : null;
}

/** The reason behind a refused attempt (problem type of the API), or null for other errors. */
export function reasonFromProblem(problem: unknown): ShareReason | null {
  const type = (problem as { type?: string } | null | undefined)?.type ?? "";
  const code = type.split("/").pop() ?? "";
  if (code === "org-unverified") return "unverified";
  if (code === "plan-required") return "plan";
  return (REASONS as readonly string[]).includes(code) ? (code as ShareReason) : null;
}

/** The choices for how long a link stays valid; 30 days unless chosen (SPEC 7.8). */
export const EXPIRY_DAYS = [1, 7, 30, 90] as const;
export const DEFAULT_DAYS = 30;

export function daysLeft(expiresAt: string, now = Date.now()): number {
  return Math.max(0, Math.ceil((Date.parse(expiresAt) - now) / 86_400_000));
}

export interface LinkLike {
  kind: string;
  target_id: string;
  revoked_at?: string | null;
  expires_at: string;
  token?: string | null;
}

/** The link of this content that still works and can be copied again (no second link). */
export function liveLink<L extends LinkLike>(links: readonly L[] | null | undefined, kind: ShareKind, targetId: string, now = Date.now()): L | null {
  return links?.find((l) => l.kind === kind && l.target_id === targetId && !l.revoked_at && Date.parse(l.expires_at) > now && l.token) ?? null;
}

/**
 * Link previews of the chats (WhatsApp, Signal, iMessage, Telegram, Slack …) fetch the page to
 * build the card. They are no viewers: the page does not count them and renders the tags only.
 */
const PREVIEW_BOTS = /WhatsApp|facebookexternalhit|Facebot|meta-externalagent|Twitterbot|TelegramBot|Slackbot|Discordbot|LinkedInBot|SkypeUriPreview|Signal|Threema|Iframely|Embedly|redditbot|Applebot|bitlybot|vkShare|Pinterestbot|Google-PageRenderer|Googlebot|bingbot|DuckDuckBot/i;

export function isPreviewBot(userAgent: string | null | undefined): boolean {
  return Boolean(userAgent && PREVIEW_BOTS.test(userAgent));
}

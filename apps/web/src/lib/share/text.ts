/**
 * Teilen im Teamchat (K20, docs/research/R2-teilen-im-chat.md): the prepared chat text, one short
 * sentence with at most one emoji and the link on its own line (WhatsApp builds the preview from
 * the first link). The text names teams, results and titles, never people.
 */

export type ShareKind = "play" | "match" | "playlist" | "highlight" | "scene" | "collection";

export const SHARE_KINDS: readonly ShareKind[] = ["play", "match", "playlist", "highlight", "scene", "collection"];

/** A translator at the root of the messages (`useTranslations()` or `getTranslations()`). */
export type T = (key: string, values?: Record<string, string | number>) => string;

export interface ShareInfo {
  kind: ShareKind;
  /** the title of what is shared (collection, scene, play) */
  title: string;
  team?: string | null;
  opponent?: string | null;
  score?: readonly number[] | null;
  /** scenes of a collection or playlist */
  scenes?: number | null;
}

const scoreOf = (s: readonly number[] | null | undefined) => (s && s.length === 2 ? `${s[0]}:${s[1]}` : null);

/** The sentence before the link. */
export function chatText(t: T, info: ShareInfo): string {
  const score = scoreOf(info.score);
  const title = info.title.trim();
  switch (info.kind) {
    case "scene":
      return t("share.chat.scene", { title });
    case "collection":
    case "playlist":
      return info.scenes ? t("share.chat.run", { title, n: info.scenes }) : t("share.chat.runEmpty", { title });
    case "highlight":
      return info.opponent && score ? t("share.chat.highlightScore", { opponent: info.opponent, score }) : t("share.chat.highlight", { team: info.team ?? title });
    case "match":
      return info.opponent && score
        ? t("share.chat.matchScore", { team: info.team ?? "", opponent: info.opponent, score })
        : t("share.chat.match", { title });
    case "play":
      return t("share.chat.play", { title });
  }
}

/** Sentence and link, ready for the chat. */
export function chatMessage(t: T, info: ShareInfo, url: string): string {
  return `${chatText(t, info)}\n${url}`;
}

/** WhatsApp with the text filled in; the coach picks the chat and sends it himself. */
export function whatsappHref(message: string): string {
  return `https://wa.me/?text=${encodeURIComponent(message)}`;
}

/** The link to a shared page. */
export function shareUrl(origin: string, token: string): string {
  return `${origin.replace(/\/$/, "")}/s/${token}`;
}

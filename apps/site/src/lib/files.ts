/** The sentences that depend on a switch, filled into the texts as {pause}, {upload}, {fileNeed}, {fileNot}, {state}. */
import type { Messages } from "@/messages/de";
import { HTML_LANG, LOCALES, messages } from "@/lib/i18n";
import { LAUNCHED, MULTI_FILE, SITE_UPDATED } from "@/lib/site";

/** The launch state sentence (LAUNCHED), with the date of SITE_UPDATED in the language of m. */
export function launchState(m: Messages): string {
  if (LAUNCHED) return m.facts.launchLive;
  const locale = LOCALES.find((l) => messages(l) === m) ?? "de";
  const date = new Intl.DateTimeFormat(HTML_LANG[locale], { dateStyle: "long", timeZone: "Europe/Zurich" }).format(new Date(SITE_UPDATED));
  return m.facts.launchPre.replace("{date}", date);
}

export function fileVars(m: Messages): Record<string, string> {
  return {
    state: launchState(m),
    pause: MULTI_FILE ? m.filming.pauseMulti : m.filming.pause,
    upload: MULTI_FILE ? m.filming.uploadMulti : m.filming.upload,
    fileNeed: MULTI_FILE ? m.facts.fileNeedMulti : m.facts.fileNeed,
    fileNot: MULTI_FILE ? "" : m.facts.fileNot,
  };
}

/** «Das noch nicht»: the item about a second file only while it is true. */
export function notList(m: Messages): string[] {
  return MULTI_FILE ? m.honest.not : [...m.honest.not, m.honest.notFiles];
}

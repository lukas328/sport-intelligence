/** Context help (addendum 01, 4.11): which help article fits a screen. Slugs are the help centre's. */
const RULES: [RegExp, string][] = [
  [/\/assistant$/, "frag-deine-daten"],
  [/\/matrix$/, "statistik-matrix"],
  [/\/training$/, "training-planen"],
  [/\/schedule$/, "training-planen"],
  [/\/presentations\//, "praesentation"],
  [/\/presentations$/, "praesentation"],
  [/\/search$/, "tags-und-filter"],
  [/\/feed/, "deine-szenen"],
  [/\/consents$/, "einwilligungen"],
  [/\/scouting$/, "vorbereitungsbericht"],
  [/\/live$/, "live-erfassung"],
  [/\/matches\/[^/]+$/, "analyse-lesen"],
  [/\/matches$/, "video-hochladen"],
  [/\/plays/, "taktiktafel"],
  [/\/(settings|club)/, "rollen-und-rechte"],
  [/\/teams\/[^/]+$/, "kader"],
];

export function helpSlug(pathname: string): string {
  return RULES.find(([re]) => re.test(pathname))?.[1] ?? "erste-schritte";
}

const LOCALE_PATH: Record<string, string> = { "de-CH": "de", fr: "fr", en: "en" };

export function helpUrl(base: string, locale: string, pathname: string): string {
  return `${base.replace(/\/hilfe$/, "")}/${LOCALE_PATH[locale] ?? "de"}/hilfe/${helpSlug(pathname)}`;
}

/** Blog posts (addendum 01, 4.13); bodies in content/blog/{locale}/{slug}.mdx. */
import type { HelpLocale } from "../help";

export interface BlogPost {
  slug: string;
  date: string; // ISO date
  updated?: string; // ISO date of the last change
  /** merged into another page (path without language): the post forwards there and leaves the sitemap */
  movedTo?: string;
  title: Record<HelpLocale, string>;
  summary: Record<HelpLocale, string>;
}

export const BLOG: BlogPost[] = [
  {
    slug: "spiele-filmen-mit-dem-handy",
    date: "2026-10-27",
    movedTo: "ratgeber/handballspiel-filmen",
    title: {
      de: "Spiele filmen mit dem Handy: fünf Regeln",
      fr: "Filmer un match avec son téléphone : cinq règles",
      en: "Filming matches with a phone: five rules",
    },
    summary: {
      de: "Eine gute Aufnahme braucht kein teures Material. Diese fünf Regeln machen den grössten Unterschied.",
      fr: "Un bon enregistrement ne demande pas de matériel coûteux. Ces cinq règles font la plus grande différence.",
      en: "A good recording needs no expensive gear. These five rules make the biggest difference.",
    },
  },
  {
    slug: "warum-wir-unsicherheit-zeigen",
    date: "2026-11-03",
    updated: "2026-11-17",
    title: {
      de: "Warum die Analyse dich fragt, wo sie unsicher ist",
      fr: "Pourquoi l'analyse te demande là où elle hésite",
      en: "Why the analysis asks you where it is unsure",
    },
    summary: {
      de: "Die Analyse schlägt vor und fragt nur, wo sie unsicher ist: ein paar Fragen statt Tor für Tor, jede Zahl mit ihrer Basis. Ein Blick hinter die Kulissen.",
      fr: "L'analyse propose et te demande là où elle hésite : quelques questions plutôt que but après but. Chaque chiffre est donné avec sa base. Un regard en coulisses.",
      en: "The analysis suggests and asks you where it is unsure: a few questions instead of goal by goal. Every number comes with its base. A look behind the scenes.",
    },
  },
];

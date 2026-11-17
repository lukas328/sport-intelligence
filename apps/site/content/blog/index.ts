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
      de: "Warum du jedes Tor selbst bestätigst",
      fr: "Pourquoi tu confirmes toi-même chaque but",
      en: "Why you confirm every goal yourself",
    },
    summary: {
      de: "Die Analyse schlägt vor, du bestätigst. So stimmt jedes Tor, und jede Zahl steht mit ihrer Basis da. Ein Blick hinter die Kulissen.",
      fr: "L'analyse propose, tu confirmes. Ainsi chaque but est juste, et chaque chiffre est donné avec sa base. Un regard en coulisses.",
      en: "The analysis suggests, you confirm. So every goal is right, and every number comes with its base. A look behind the scenes.",
    },
  },
];

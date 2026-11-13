/** Blog posts (addendum 01, 4.13); bodies in content/blog/{locale}/{slug}.mdx. */
import type { HelpLocale } from "../help";

export interface BlogPost {
  slug: string;
  date: string; // ISO date
  updated?: string; // ISO date of the last change
  title: Record<HelpLocale, string>;
  summary: Record<HelpLocale, string>;
}

export const BLOG: BlogPost[] = [
  {
    slug: "spiele-filmen-mit-dem-handy",
    date: "2026-10-27",
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
    title: {
      de: "Warum wir zeigen, wo die Analyse unsicher ist",
      fr: "Pourquoi nous montrons où l'analyse est incertaine",
      en: "Why we show where the analysis is uncertain",
    },
    summary: {
      de: "Automatische Erkennung macht Fehler. Wir markieren sie, statt sie zu verstecken. Ein Blick hinter die Kulissen.",
      fr: "La détection automatique fait des erreurs. Nous les signalons au lieu de les cacher. Un regard en coulisses.",
      en: "Automatic detection makes mistakes. We flag them instead of hiding them. A look behind the scenes.",
    },
  },
];

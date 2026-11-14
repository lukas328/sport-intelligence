/**
 * Structured data (schema.org JSON-LD). Only what the page also shows: no ratings, no reviews, no
 * invented authors, no price while the plan table is a placeholder (PRICES_FINAL). Every node with
 * an @id is defined once per page and referenced elsewhere.
 */
import plans from "@handball/plans";
import { HTML_LANG, type Locale } from "@/lib/i18n";
import { PRICES_FINAL, SITE_NAME, SITE_URL, SUPPORT_EMAIL, pageUrl } from "@/lib/site";

type Node = Record<string, unknown>;

export const ORG_ID = `${SITE_URL}/#organisation`;
export const WEBSITE_ID = `${SITE_URL}/#website`;
export const APP_ID = `${SITE_URL}/#app`;

export function graph(...nodes: (Node | null | undefined | false)[]): Node {
  return { "@context": "https://schema.org", "@graph": nodes.filter(Boolean) };
}

export function organization(): Node {
  return {
    "@type": "Organization",
    "@id": ORG_ID,
    name: SITE_NAME,
    url: `${SITE_URL}/`,
    logo: { "@type": "ImageObject", url: `${SITE_URL}/icon.png`, width: 512, height: 512 },
    email: SUPPORT_EMAIL,
    contactPoint: { "@type": "ContactPoint", contactType: "customer support", email: SUPPORT_EMAIL, availableLanguage: ["de", "fr", "en"] },
  };
}

export function website(locale: Locale): Node {
  return {
    "@type": "WebSite",
    "@id": WEBSITE_ID,
    name: SITE_NAME,
    url: `${SITE_URL}/`,
    inLanguage: ["de-CH", "fr-CH", "en"],
    publisher: { "@id": ORG_ID },
    mainEntityOfPage: pageUrl(locale),
  };
}

/** The product with its plans, named and described as on the pricing page; prices only once final. */
export function softwareApplication(locale: Locale, description: string, planText: Record<string, { name: string; text: string }>): Node {
  return {
    "@type": "SoftwareApplication",
    "@id": APP_ID,
    name: SITE_NAME,
    description,
    applicationCategory: "SportsApplication",
    operatingSystem: "Web browser",
    url: pageUrl(locale),
    inLanguage: ["de-CH", "fr-CH", "en"],
    publisher: { "@id": ORG_ID },
    offers: plans.plans.map((p) => ({
      "@type": "Offer",
      name: planText[p.plan]?.name ?? p.plan,
      description: planText[p.plan]?.text,
      url: pageUrl(locale, "preise"),
      ...(PRICES_FINAL ? { price: p.price_chf_month, priceCurrency: plans.currency } : {}),
    })),
  };
}

export function breadcrumbs(items: [string, string][]): Node {
  return {
    "@type": "BreadcrumbList",
    itemListElement: items.map(([name, url], i) => ({ "@type": "ListItem", position: i + 1, name, item: url })),
  };
}

export function webPage(locale: Locale, path: string, name: string, description: string, modified?: string, type = "WebPage"): Node {
  return {
    "@type": type,
    "@id": `${pageUrl(locale, path)}#seite`,
    url: pageUrl(locale, path),
    name,
    description,
    inLanguage: HTML_LANG[locale],
    isPartOf: { "@id": WEBSITE_ID },
    ...(modified ? { dateModified: modified } : {}),
  };
}

/** Guides and blog posts: the publisher is the organisation; no person is named as author. */
export function article(
  locale: Locale,
  path: string,
  a: { headline: string; description: string; published: string; modified?: string; type?: "Article" | "BlogPosting" | "TechArticle" },
): Node {
  const url = pageUrl(locale, path);
  return {
    "@type": a.type ?? "Article",
    "@id": `${url}#artikel`,
    headline: a.headline,
    description: a.description,
    datePublished: a.published,
    dateModified: a.modified ?? a.published,
    inLanguage: HTML_LANG[locale],
    url,
    mainEntityOfPage: url,
    image: `${SITE_URL}/og.png`,
    author: { "@id": ORG_ID },
    publisher: { "@id": ORG_ID },
    isPartOf: { "@id": WEBSITE_ID },
  };
}

/** Questions and answers exactly as the page shows them (plain text). */
export function faqPage(locale: Locale, path: string, items: { q: string; a: string }[]): Node | null {
  if (!items.length) return null;
  return {
    "@type": "FAQPage",
    "@id": `${pageUrl(locale, path)}#fragen`,
    inLanguage: HTML_LANG[locale],
    mainEntity: items.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })),
  };
}

export interface HowToData {
  name: string;
  description?: string;
  totalTime?: string; // ISO 8601 duration
  tools?: string[];
  steps: { name: string; text: string }[];
}

/** Steps exactly as the page shows them. */
export function howTo(locale: Locale, path: string, h: HowToData): Node {
  const url = pageUrl(locale, path);
  return {
    "@type": "HowTo",
    "@id": `${url}#anleitung`,
    name: h.name,
    ...(h.description ? { description: h.description } : {}),
    inLanguage: HTML_LANG[locale],
    ...(h.totalTime ? { totalTime: h.totalTime } : {}),
    ...(h.tools?.length ? { tool: h.tools.map((name) => ({ "@type": "HowToTool", name })) } : {}),
    step: h.steps.map((s, i) => ({ "@type": "HowToStep", position: i + 1, name: s.name, text: s.text, url: `${url}#schritt-${i + 1}` })),
  };
}

/**
 * /llms.txt and /llms-full.txt (proposal at llmstxt.org): what the product is, for whom, what it
 * can and cannot do, and the important pages, in Markdown. Built from the same texts as the pages
 * (messages, facts, guides), so they never say more than the site. Google says it ignores these
 * files; other assistants may read them. See docs/site/SEO.md.
 */
import plans from "@handball/plans";
import { factRows } from "@/lib/facts";
import { fileVars, notList } from "@/lib/files";
import { fmt, messages, type Locale } from "@/lib/i18n";
import { SITE_NAME, SITE_UPDATED, pageUrl } from "@/lib/site";
import { BLOG } from "../../content/blog";
import { GUIDES } from "../../content/ratgeber";
import { HELP } from "../../content/help";

const link = (title: string, url: string, note?: string) => `- [${title}](${url})${note ? `: ${note}` : ""}`;

function pages(locale: Locale): string[] {
  const m = messages(locale);
  return [
    link(m.facts.title, pageUrl(locale, "fakten"), m.facts.description),
    link(m.seo.how.title, pageUrl(locale, "so-funktioniert-es"), m.seo.how.description),
    link(m.seo.filming.title, pageUrl(locale, "aufnahme"), m.seo.filming.description),
    link(m.seo.pricing.title, pageUrl(locale, "preise"), m.seo.pricing.description),
    link(m.seo.data.title, pageUrl(locale, "daten"), m.seo.data.description),
    link(m.seo.faq.title, pageUrl(locale, "hilfe"), m.seo.faq.description),
    link(m.seo.demo.title, pageUrl(locale, "demo"), m.seo.demo.description),
    link(m.us.title, pageUrl(locale, "ueber-uns"), m.us.homeText),
  ];
}

function guides(locale: Locale): string[] {
  return GUIDES.filter((g) => g.locales.includes(locale)).map((g) => link(g.title[locale]!, pageUrl(locale, `ratgeber/${g.slug}`), g.answer[locale]));
}

export function llmsTxt(): string {
  const de = messages("de");
  const rows = factRows("de");
  const get = (k: string) => rows.find((r) => r.k === k)?.v ?? "";
  return [
    `# ${SITE_NAME}`,
    "",
    `> ${de.facts.lead}`,
    "",
    `Stand: ${SITE_UPDATED}. Sprachen: Deutsch (de-CH), Französisch (fr-CH), Englisch. Für wen: ${get("Für wen")}`,
    "",
    `Wer dahinter steht: ${de.us.homeText}`,
    "",
    "## Kann",
    "",
    ...de.honest.can.map((x) => `- ${x}`),
    "",
    "## Kann noch nicht",
    "",
    ...notList(de).map((x) => `- ${x}`),
    "",
    `Preisstand: ${get("Preisstand")}`,
    "",
    "## Wichtige Seiten",
    "",
    ...pages("de"),
    "",
    "## Ratgeber",
    "",
    ...guides("de"),
    "",
    "## Other languages",
    "",
    link("Facts at a glance (English)", pageUrl("en", "fakten")),
    link("L'essentiel en bref (français)", pageUrl("fr", "fakten")),
    "",
    "## Optional",
    "",
    link("Ausführliche Fassung", `${pageUrl("de").replace(/\/de\/$/, "")}/llms-full.txt`),
    link("Blog", pageUrl("de", "blog")),
    "",
  ].join("\n");
}

function section(locale: Locale): string[] {
  const m = messages(locale);
  const team = plans.plans.find((p) => p.plan === "team")!;
  return [
    `## ${m.facts.title} (${locale})`,
    "",
    m.facts.lead,
    "",
    ...factRows(locale).map((r) => `- **${r.k}:** ${r.v}`),
    "",
    `### ${m.honest.canTitle}`,
    "",
    ...m.honest.can.map((x) => `- ${x}`),
    "",
    `### ${m.honest.notTitle}`,
    "",
    ...notList(m).map((x) => `- ${x}`),
    "",
    m.honest.note,
    "",
    `### ${m.faq.head}`,
    "",
    ...m.faq.items.flatMap((f) => [`**${f.q}** ${fmt(f.a, { month: team.price_chf_month, year: team.price_chf_year, ...fileVars(m) })}`, ""]),
    `### ${m.guides.title}`,
    "",
    ...guides(locale),
    "",
    `### ${m.nav.how}`,
    "",
    ...pages(locale),
    "",
  ];
}

export function llmsFullTxt(): string {
  return [
    `# ${SITE_NAME}`,
    "",
    `> ${messages("de").facts.lead}`,
    "",
    `Stand: ${SITE_UPDATED}. Diese Datei fasst die Website zusammen; sie sagt nichts, was nicht auch auf den Seiten steht.`,
    "",
    ...section("de"),
    ...section("fr"),
    ...section("en"),
    "## Anleitungen zur App (Deutsch)",
    "",
    ...HELP.filter((h) => h.listed !== false).map((h) => link(h.title.de, pageUrl("de", `hilfe/${h.slug}`), h.summary.de)),
    "",
    "## Blog (Deutsch)",
    "",
    ...BLOG.map((p) => link(p.title.de, pageUrl("de", `blog/${p.slug}`), p.summary.de)),
    "",
  ].join("\n");
}

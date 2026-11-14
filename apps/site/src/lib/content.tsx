import type { MDXComponents } from "mdx/types";
import Link from "next/link";
import type { ComponentType } from "react";
import type { Locale } from "@/lib/i18n";
import { resolveHref } from "@/lib/links";
import { slugify } from "@/lib/slug";
import type { HowToData } from "@/lib/schema";
import * as figures from "@/components/figures";

type Body = ComponentType<{ components?: MDXComponents }>;

/** MDX bodies; the template literals let the bundler include every file of the folder. */
export async function helpBody(locale: Locale, slug: string): Promise<Body> {
  return (await import(`../../content/help/${locale}/${slug}.mdx`)).default as Body;
}

export async function blogBody(locale: Locale, slug: string): Promise<Body> {
  return (await import(`../../content/blog/${locale}/${slug}.mdx`)).default as Body;
}

export async function legalBody(locale: Locale, page: string): Promise<Body> {
  return (await import(`../../content/legal/${locale}/${page}.mdx`)).default as Body;
}

export interface GuideModule {
  default: Body;
  /** short questions and answers shown at the end of the guide (and as FAQPage) */
  faq?: { q: string; a: string }[];
  /** the steps the guide shows with <Steps items={howto.steps} /> (and as HowTo) */
  howto?: HowToData;
}

export async function guideModule(locale: Locale, slug: string): Promise<GuideModule> {
  return (await import(`../../content/ratgeber/${locale}/${slug}.mdx`)) as GuideModule;
}

const tableLabel: Record<Locale, string> = { de: "Tabelle, seitlich verschiebbar", fr: "Tableau, défilement horizontal", en: "Table, scrolls sideways" };

export function mdxComponents(locale: Locale, folder: string): MDXComponents {
  return {
    ...figures,
    // wide tables scroll inside their own box instead of widening the page
    table: (props) => (
      <div className="table-scroll" role="region" aria-label={tableLabel[locale]} tabIndex={0}>
        <table {...props} />
      </div>
    ),
    // level-two headings get the same ids as the table of contents (lib/slug.ts)
    h2: ({ children }) => <h2 id={typeof children === "string" ? slugify(children) : undefined}>{children}</h2>,
    a: ({ href = "", children }) => {
      const target = resolveHref(href, locale, folder);
      return target.startsWith("/") ? <Link href={target}>{children}</Link> : <a href={target}>{children}</a>;
    },
  };
}

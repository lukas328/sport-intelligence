import type { MDXComponents } from "mdx/types";
import Link from "next/link";
import type { ComponentType } from "react";
import type { Locale } from "@/lib/i18n";
import { resolveHref } from "@/lib/links";
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

export function mdxComponents(locale: Locale, folder: string): MDXComponents {
  return {
    ...figures,
    a: ({ href = "", children }) => {
      const target = resolveHref(href, locale, folder);
      return target.startsWith("/") ? <Link href={target}>{children}</Link> : <a href={target}>{children}</a>;
    },
  };
}

import type { MDXComponents } from "mdx/types";
import Link from "next/link";
import type { ComponentType } from "react";
import type { Locale } from "@/lib/i18n";
import { resolveHref } from "@/lib/links";

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

export function mdxComponents(locale: Locale, folder: string): MDXComponents {
  return {
    a: ({ href = "", children }) => {
      const target = resolveHref(href, locale, folder);
      return target.startsWith("/") ? <Link href={target}>{children}</Link> : <a href={target}>{children}</a>;
    },
  };
}

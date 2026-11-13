"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

/** The destinations, the current one with the active marker (a slanted band in the club colour). */
export function NavLinks({ locale, links, stacked = false }: { locale: string; links: [string, string][]; stacked?: boolean }) {
  const path = usePathname() ?? "";
  return (
    <ul className={cn(stacked ? "flex flex-col" : "flex flex-wrap items-center gap-x-1")}>
      {links.map(([slug, label]) => {
        const href = `/${locale}/${slug}/`;
        const on = path.startsWith(`/${locale}/${slug}`);
        return (
          <li key={slug}>
            <Link
              href={href}
              aria-current={on ? "page" : undefined}
              className={cn(
                "font-slant relative inline-flex min-h-12 items-center whitespace-nowrap px-2 text-[1.125rem] hover:underline",
                stacked && "w-full border-b border-rule px-0 text-[1.375rem]",
                on ? "text-ink" : "text-ink-2",
              )}
            >
              {label}
              {on && <i aria-hidden className={cn("mark-band absolute bottom-0 h-1.5", stacked ? "left-0 w-16" : "inset-x-2")} />}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

/** The same page in the other languages (names written out, not abbreviations). */
export function LangLinks({ locale, names }: { locale: string; names: Record<string, string> }) {
  const path = usePathname() ?? `/${locale}/`;
  return (
    <ul className="mt-2">
      {Object.entries(names).map(([l, name]) => (
        <li key={l}>
          <Link
            href={path.replace(new RegExp(`^/${locale}(?=/|$)`), `/${l}`)}
            hrefLang={l}
            lang={l}
            aria-current={l === locale ? "true" : undefined}
            className={cn("inline-flex min-h-12 min-w-12 items-center underline-offset-4", l === locale ? "font-bold underline" : "hover:underline")}
          >
            {name}
          </Link>
        </li>
      ))}
    </ul>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

/** The destinations, the current one with the active marker (a slanted band in the club colour). */
export function NavLinks({
  locale,
  links,
  stacked = false,
}: {
  locale: string;
  links: [string, string][];
  stacked?: boolean;
}) {
  const path = usePathname() ?? "";
  return (
    <ul className={cn(stacked ? "flex flex-col" : "flex items-center xl:gap-x-1")}>
      {links.map(([slug, label]) => {
        // "" is the start page: current only on the start page itself
        const href = slug ? `/${locale}/${slug}/` : `/${locale}/`;
        const on = slug
          ? path.startsWith(`/${locale}/${slug}`)
          : path.replace(/\/$/, "") === `/${locale}`;
        return (
          <li key={slug}>
            <Link
              href={href}
              aria-current={on ? "page" : undefined}
              className={cn(
                "relative inline-flex min-h-12 items-center whitespace-nowrap px-2 text-base font-semibold text-ink hover:underline xl:px-2.5 xl:text-[1.125rem]",
                stacked &&
                  "w-full border-b border-rule px-0 text-[1.375rem] xl:px-0 xl:text-[1.375rem]",
              )}
            >
              {label}
              {on && (
                <i
                  aria-hidden
                  className={cn(
                    "mark-band absolute bottom-0 h-1.5",
                    stacked ? "left-0 w-16" : "inset-x-2",
                  )}
                />
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

/** Where a link to the same page in another language goes (a guide missing there: that language's guides). */
function useLangTarget(locale: string, missing: Record<string, string[]>) {
  const path = usePathname() ?? `/${locale}/`;
  const guide = path.match(/\/ratgeber\/([a-z0-9-]+)\/?$/)?.[1];
  return (l: string) =>
    guide && missing[guide]?.includes(l)
      ? `/${l}/ratgeber/`
      : path.replace(new RegExp(`^/${locale}(?=/|$)`), `/${l}`);
}

/**
 * The language switch in the top bar (BEFUNDE-2 L3): DE · FR · EN, the current one bold and
 * underlined. Each link is named in its own language for screen readers. `big` is the phone
 * menu's form: three wide buttons in a row.
 */
export function LangSwitch({
  locale,
  names,
  label,
  missing = {},
  big = false,
  dark = false,
}: {
  locale: string;
  names: Record<string, string>;
  label: string;
  missing?: Record<string, string[]>;
  big?: boolean;
  /** on the ink strip of the desktop bar */
  dark?: boolean;
}) {
  const target = useLangTarget(locale, missing);
  return (
    <ul aria-label={label} className={cn("flex items-center", big ? "gap-2" : "font-mono")}>
      {Object.entries(names).map(([l, name], i) => (
        <li key={l} className="flex items-center">
          {!big && i > 0 && (
            <span aria-hidden className={cn("px-0.5", dark ? "text-[#8d9198]" : "text-ink-2")}>
              ·
            </span>
          )}
          <Link
            href={target(l)}
            hrefLang={l}
            lang={l}
            aria-label={name}
            aria-current={l === locale ? "true" : undefined}
            className={cn(
              "inline-flex min-h-12 items-center justify-center text-base font-semibold uppercase",
              big
                ? cn(
                    "min-w-[4.5rem] border-2 border-ink px-4",
                    l === locale ? "bg-ink text-ground" : "bg-paper hover:bg-ink/10",
                  )
                : cn(
                    "min-h-11 min-w-9 px-1 underline-offset-[6px]",
                    l === locale
                      ? "font-bold underline decoration-2"
                      : dark
                        ? "text-[#c4c8cd] hover:text-ground hover:underline"
                        : "text-ink-2 hover:text-ink hover:underline",
                  ),
            )}
          >
            {l}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** The same page in the other languages (names written out, not abbreviations). */
export function LangLinks({
  locale,
  names,
  missing = {},
}: {
  locale: string;
  names: Record<string, string>;
  missing?: Record<string, string[]>;
}) {
  // a guide that does not exist in a language: that language's list of guides instead
  const target = useLangTarget(locale, missing);
  return (
    <ul className="mt-2">
      {Object.entries(names).map(([l, name]) => (
        <li key={l}>
          <Link
            href={target(l)}
            hrefLang={l}
            lang={l}
            aria-current={l === locale ? "true" : undefined}
            className={cn(
              "inline-flex min-h-12 min-w-12 items-center underline-offset-4",
              l === locale ? "font-bold underline" : "hover:underline",
            )}
          >
            {name}
          </Link>
        </li>
      ))}
    </ul>
  );
}

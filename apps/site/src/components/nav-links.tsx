"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
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
    <ul className={cn(stacked ? "flex flex-col" : "flex items-center")}>
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
                "relative inline-flex min-h-12 items-center whitespace-nowrap px-1.5 text-base font-semibold text-ink hover:underline xl:px-2 xl:text-[1.0625rem]",
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
                    stacked ? "left-0 w-16" : "inset-x-1.5 xl:inset-x-2",
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
 * The language in the phone menu (BEFUNDE-2 L3): three wide buttons DE, FR, EN, the current one
 * filled. Each link is named in its own language for screen readers.
 */
export function LangSwitch({
  locale,
  names,
  label,
  missing = {},
}: {
  locale: string;
  names: Record<string, string>;
  label: string;
  missing?: Record<string, string[]>;
}) {
  const target = useLangTarget(locale, missing);
  return (
    <ul aria-label={label} className="flex items-center gap-2">
      {Object.entries(names).map(([l, name]) => (
        <li key={l} className="flex items-center">
          <Link
            href={target(l)}
            hrefLang={l}
            lang={l}
            aria-label={name}
            aria-current={l === locale ? "true" : undefined}
            className={cn(
              "inline-flex min-h-12 min-w-[4.5rem] items-center justify-center border-2 border-ink px-4 text-base font-semibold uppercase",
              l === locale ? "bg-ink text-ground" : "bg-paper hover:bg-ink/10",
            )}
          >
            {l}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/**
 * The language in the bar from a laptop on (BEFUNDE-3 U2): a compact button with the current
 * language («DE») that opens the three languages, each written out. A disclosure, not an ARIA
 * menu: the button says whether it is open (aria-expanded), the arrow keys move between the
 * languages, Escape closes it and gives the focus back to the button, and a click outside or the
 * focus leaving closes it too. Without JavaScript the languages stay in the footer.
 */
export function LangMenu({
  locale,
  names,
  label,
  missing = {},
}: {
  locale: string;
  names: Record<string, string>;
  label: string;
  missing?: Record<string, string[]>;
}) {
  const target = useLangTarget(locale, missing);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open) return;
    const outside = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  const links = () => Array.from(box.current?.querySelectorAll<HTMLAnchorElement>("li a") ?? []);
  const focusLink = (pick: (all: HTMLAnchorElement[], at: number) => number) => {
    const all = links();
    const at = all.indexOf(document.activeElement as HTMLAnchorElement);
    all[(pick(all, at) + all.length) % all.length]?.focus();
  };
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape" && open) {
      e.preventDefault();
      setOpen(false);
      button.current?.focus();
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const down = e.key === "ArrowDown";
      if (!open) {
        setOpen(true);
        // the list renders on the next frame
        requestAnimationFrame(() => focusLink((all) => (down ? 0 : all.length - 1)));
      } else focusLink((_, at) => (at < 0 ? (down ? 0 : -1) : at + (down ? 1 : -1)));
    } else if ((e.key === "Home" || e.key === "End") && open) {
      e.preventDefault();
      focusLink((all) => (e.key === "Home" ? 0 : all.length - 1));
    }
  };
  return (
    <div
      ref={box}
      className="relative"
      onKeyDown={onKeyDown}
      onBlur={(e) => {
        if (open && !box.current?.contains(e.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex min-h-12 items-center gap-1.5 px-1.5 font-mono text-base font-semibold uppercase hover:underline xl:px-2"
      >
        <span className="sr-only">{label} </span>
        {locale}
        <svg viewBox="0 0 12 8" aria-hidden className="h-2 w-3">
          <path d={open ? "M1 6.5 6 1.5l5 5" : "M1 1.5 6 6.5l5-5"} fill="none" stroke="currentColor" strokeWidth={2} />
        </svg>
      </button>
      <ul
        id={id}
        aria-label={label}
        hidden={!open}
        className="absolute top-full right-0 z-40 mt-1 min-w-[13rem] border-2 border-ink bg-paper py-1 shadow-[4px_4px_0_var(--ink)]"
      >
        {Object.entries(names).map(([l, name]) => (
          <li key={l}>
            <Link
              href={target(l)}
              hrefLang={l}
              lang={l}
              aria-current={l === locale ? "true" : undefined}
              onClick={() => setOpen(false)}
              className={cn(
                "flex min-h-12 items-center gap-3 px-4 text-base font-semibold outline-offset-[-3px] hover:bg-ink/10 focus-visible:bg-ink/10",
                l === locale && "underline decoration-2 underline-offset-[6px]",
              )}
            >
              <span aria-hidden className="w-7 font-mono text-ink-2 uppercase">
                {l}
              </span>
              {name}
            </Link>
          </li>
        ))}
      </ul>
    </div>
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

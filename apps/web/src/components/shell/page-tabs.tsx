"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

/** The one level of tabs of a page with sub-routes (Ich, Verein): underline links, all widths. */
export function PageTabs({ label, items }: { label: string; items: { key: string; href: string; label: string }[] }) {
  const path = usePathname();
  // the longest matching href is the active tab (/me matches /me/security too)
  const active = items.filter((it) => path === it.href || path.startsWith(`${it.href}/`)).sort((a, b) => b.href.length - a.href.length)[0]?.key;
  if (items.length < 2) return null;
  return (
    <nav aria-label={label} className="scrollbar-none -mx-1 overflow-x-auto border-b border-foreground/15 px-1">
      <ul className="inline-flex gap-5">
        {items.map((it) => {
          const on = it.key === active;
          return (
            <li key={it.key}>
              <Link
                href={it.href}
                aria-current={on ? "page" : undefined}
                className={cn(
                  "-mb-px block min-h-11 whitespace-nowrap border-b-2 pt-2.5 text-[0.9375rem] font-semibold transition-colors",
                  on ? "border-foreground text-foreground" : "border-transparent text-muted hover:text-foreground",
                )}
              >
                {it.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

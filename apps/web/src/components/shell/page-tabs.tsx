"use client";

import { usePathname } from "next/navigation";
import { LinkTabs } from "@/components/anlauf/blocks";

/** The one level of tabs of a page with sub-routes (Ich, Verein). */
export function PageTabs({ label, items }: { label: string; items: { key: string; href: string; label: string }[] }) {
  const path = usePathname();
  // the longest matching href is the active tab (/me matches /me/security too)
  const active = items.filter((it) => path === it.href || path.startsWith(`${it.href}/`)).sort((a, b) => b.href.length - a.href.length)[0]?.key ?? null;
  if (items.length < 2) return null;
  return <LinkTabs label={label} items={items} active={active} />;
}

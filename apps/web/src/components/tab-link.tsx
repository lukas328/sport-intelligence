"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function TabLink({ href, exact, children }: { href: string; exact?: boolean; children: ReactNode }) {
  const path = usePathname();
  const active = exact ? path === href : path === href || path.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn("font-slant relative flex min-h-[54px] items-center px-3 text-[17px] whitespace-nowrap no-underline md:text-xl", active ? "text-ink" : "text-ink-2 hover:text-ink")}
    >
      {children}
      {active && <span aria-hidden data-mark="" className="mark-band absolute right-2.5 -bottom-0.5 left-2.5 h-1.5" />}
    </Link>
  );
}

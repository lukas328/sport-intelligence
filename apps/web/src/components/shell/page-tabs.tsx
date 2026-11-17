"use client";

import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { LinkTabs } from "@/components/anlauf/blocks";
import { useShell } from "./context";

/** The one level of tabs of a page with sub-routes (Ich, Verein). */
export function PageTabs({ label, items }: { label: string; items: { key: string; href: string; label: string }[] }) {
  const path = usePathname();
  // the longest matching href is the active tab (/me matches /me/security too)
  const active = items.filter((it) => path === it.href || path.startsWith(`${it.href}/`)).sort((a, b) => b.href.length - a.href.length)[0]?.key ?? null;
  if (items.length < 2) return null;
  return <LinkTabs label={label} items={items} active={active} />;
}

/** The way back from a page of the account menu (Ich, Verein) to the team's matches: those pages
 * sit outside the four destinations, so nothing in the top bar leads back (review R18). */
export function BackToTeam() {
  const t = useTranslations("shell");
  const { org, team } = useShell();
  const href = team ? `/app/${org.id}/teams/${team.id}/matches` : `/app/${org.id}`;
  return (
    <Link href={href} className="-mb-3 inline-flex min-h-11 items-center gap-1 text-[15px] font-bold text-ink" data-testid="back-to-team">
      <ChevronLeft aria-hidden className="size-4" />
      {team ? t("backToTeam", { team: team.name }) : t("matches")}
    </Link>
  );
}

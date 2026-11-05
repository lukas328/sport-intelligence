"use client";

import Link from "next/link";
import { ChevronLeft, Grid3x3 } from "lucide-react";
import { IconAsk } from "./icons";
import { buttonClass } from "@/components/ui/button";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { destOf, sectionOf, sectionsFor, type Dest, type Section } from "@/lib/nav-model";
import { cn } from "@/lib/utils";
import { useShell } from "./context";

/** Second (and last) level of navigation: a few pill links below the page title. */
export function SubNav({ label, items, active }: { label: string; items: { key: string; href: string; label: ReactNode }[]; active: string | null }) {
  return (
    <nav aria-label={label} className="scrollbar-none -mx-1 overflow-x-auto px-1 lg:hidden">
      <ul className="inline-flex gap-1">
        {items.map((it) => {
          const on = it.key === active;
          return (
            <li key={it.key}>
              <Link
                href={it.href}
                aria-current={on ? "page" : undefined}
                className={cn(
                  "block whitespace-nowrap rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
                  on ? "bg-foreground text-background" : "text-muted hover:bg-surface hover:text-foreground",
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

/** The current destination, its second level with labels and the active item. */
function useArea() {
  const t = useTranslations("shell");
  const path = usePathname();
  const { org, team, mode } = useShell();
  const dest = destOf(path, mode);
  const items = dest ? sectionsFor(dest, mode, org.id, team?.id ?? null).map((x) => ({ ...x, label: t(x.key) })) : [];
  const page: string = path.replace(/^\/app\/[^/]+(\/teams\/[^/]+)?/, "").split("/")[1] ?? "";
  return { dest, items, active: sectionOf(path), page, org, team, mode };
}

const SUBNAV_LABEL: Partial<Record<Dest, "matchSections" | "trainingSections" | "teamSections">> = {
  matches: "matchSections",
  training: "trainingSections",
  team: "teamSections",
};

/** Second level of the current destination on phones (the sidebar shows it on desktop). */
export function AreaSubNav() {
  const t = useTranslations("shell");
  const { dest, items, active } = useArea();
  if (!dest || items.length === 0) return null;
  return <SubNav label={t(SUBNAV_LABEL[dest] ?? "teamSections")} items={items} active={active} />;
}

/** Leaf pages one level below a section item, with a way back to it. */
const LEAF: Record<string, { parent: Section; title: string }> = {
  playlists: { parent: "library", title: "library.playlists" },
  presentations: { parent: "library", title: "library.presentations" },
  search: { parent: "library", title: "library.search" },
};

/** Title, phone sub navigation and leaf back link for the pages of a destination. */
export function AreaHeader({ actions, title: fallbackTitle }: { actions?: ReactNode; title?: string }) {
  const t = useTranslations("shell");
  const tr = useTranslations();
  const { dest, items, active, page, org, team } = useArea();
  const teamBase = team ? `/app/${org.id}/teams/${team.id}` : null;
  const leaf = LEAF[page];
  const seasonTools =
    teamBase && active === "season" ? (
      <>
        <Link href={`${teamBase}/matrix`} className={buttonClass("secondary", "sm")} aria-current={page === "matrix" ? "page" : undefined}>
          <Grid3x3 aria-hidden />
          {tr("palette.matrix")}
        </Link>
        <Link href={`${teamBase}/assistant`} className={buttonClass("secondary", "sm")} aria-current={page === "assistant" ? "page" : undefined}>
          <IconAsk />
          {tr("palette.ask")}
        </Link>
      </>
    ) : null;
  const heading =
    dest === "matches"
      ? { eyebrow: team?.name, title: t("matches") }
      : dest === "training"
        ? { eyebrow: team?.name, title: t("training") }
        : dest === "team" && team
          ? { eyebrow: team.season ?? org.name, title: team.name }
          : { eyebrow: undefined, title: fallbackTitle ?? "" };
  return (
    <div className="space-y-5">
      <PageHeader eyebrow={heading.eyebrow} title={heading.title} actions={actions ?? seasonTools} />
      {dest && items.length > 0 && <SubNav label={t(SUBNAV_LABEL[dest] ?? "teamSections")} items={items} active={active} />}
      {leaf && teamBase && <LeafTitle href={`${teamBase}/${leaf.parent}`} parent={leaf.parent} title={tr(leaf.title as "library.plays")} search={page === "search"} />}
    </div>
  );
}

function LeafTitle({ href, parent, title, search }: { href: string; parent: Section; title: string; search: boolean }) {
  const t = useTranslations();
  const parentLabel = parent === "library" ? t("library.title") : t(`shell.${parent}` as "shell.season");
  return (
    <div className="flex items-center gap-2 pt-2">
      <Link href={href} aria-label={t("library.back", { name: parentLabel })} className="grid size-8 place-items-center rounded-md text-muted ring-1 ring-border hover:bg-surface hover:text-foreground">
        <ChevronLeft aria-hidden className="size-4" />
      </Link>
      {search ? <span className="text-sm font-medium text-muted">{parentLabel}</span> : <h2 className="text-xl font-bold">{title}</h2>}
    </div>
  );
}

/** Team layout chrome: the header of the destination a team page belongs to. */
export function TeamChrome() {
  const { active } = useArea();
  const path = usePathname();
  if (!active) return null;
  // the season page opens with its own stage (one stage per screen, at the top)
  if (/\/season$/.test(path)) return null;
  // the fixture list has its own title and actions
  if (active === "fixtures") return <AreaSubNav />;
  return <AreaHeader />;
}

/** Header for org-level pages that sit in a destination for staff and stand alone for others. */
export function AreaOrPageHeader({ title }: { title: string }) {
  const { mode, dest, team } = useArea();
  if (mode === "staff" && (dest === "training" || (dest === "team" && team))) return <AreaHeader title={title} />;
  return <PageHeader title={title} />;
}

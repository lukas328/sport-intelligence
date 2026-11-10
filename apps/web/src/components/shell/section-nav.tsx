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

/** Second (and last) level of navigation: underline links below the page title, like the tabs. */
export function SubNav({ label, items, active }: { label: string; items: { key: string; href: string; label: ReactNode }[]; active: string | null }) {
  return (
    <nav aria-label={label} className="scrollbar-none -mx-1 overflow-x-auto border-b border-foreground/15 px-1 lg:hidden">
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
const LEAF: Record<string, { parent: Section; title: string; href?: string }> = {
  playlists: { parent: "library", title: "library.playlists" },
  presentations: { parent: "library", title: "library.presentations" },
  search: { parent: "library", title: "library.search" },
  paper: { parent: "fixtures", title: "paper.photoTitle", href: "matches" },
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
        {/* on a tool page only the other tool */}
        {page !== "matrix" && (
          <Link href={`${teamBase}/matrix`} className={buttonClass("secondary", "sm")}>
            <Grid3x3 aria-hidden />
            {tr("palette.matrix")}
          </Link>
        )}
        {page !== "assistant" && (
          <Link href={`${teamBase}/assistant`} className={buttonClass("secondary", "sm")}>
            <IconAsk />
            {tr("palette.ask")}
          </Link>
        )}
      </>
    ) : null;
  // the title names the page; the destination and the team go into the eyebrow
  const destTitle = dest === "matches" ? t("matches") : dest === "training" ? t("training") : dest === "team" ? t("team") : undefined;
  const tool = page === "matrix" ? tr("palette.matrix") : page === "assistant" ? tr("palette.ask") : null;
  const pageTitle = (leaf && tr(leaf.title as "library.plays")) || tool || items.find((i) => i.key === active)?.label || destTitle || fallbackTitle || "";
  const heading = dest
    ? { eyebrow: [destTitle, team?.name].filter(Boolean).join(" · ") || undefined, title: pageTitle }
    : { eyebrow: undefined, title: fallbackTitle ?? "" };
  return (
    <div className="space-y-5">
      {(leaf || tool) && teamBase && <BackLink href={`${teamBase}/${leaf ? leaf.href ?? leaf.parent : "season"}`} parent={leaf ? leaf.parent : "season"} />}
      <PageHeader eyebrow={heading.eyebrow} title={heading.title} actions={actions ?? seasonTools} />
      {dest && items.length > 0 && !leaf && !tool && <SubNav label={t(SUBNAV_LABEL[dest] ?? "teamSections")} items={items} active={active} />}
    </div>
  );
}

/** The way back from a page one level below a section item: a text link above the title. */
function BackLink({ href, parent }: { href: string; parent: Section }) {
  const t = useTranslations();
  const parentLabel = parent === "library" ? t("library.title") : t(`shell.${parent}` as "shell.season");
  return (
    <Link href={href} className="-mb-3 inline-flex items-center gap-1 text-sm font-medium text-muted hover:text-foreground">
      <ChevronLeft aria-hidden className="size-4" />
      {parentLabel}
    </Link>
  );
}

/** Team layout chrome: the header of the destination a team page belongs to. */
export function TeamChrome() {
  const { active, page } = useArea();
  const path = usePathname();
  if (!active) return null;
  // the official data and the join requests sit under the squad but bring their own heading
  if (page === "official" || page === "join-requests" || page === "players") return null;
  // the season page opens with its own stage (one stage per screen, at the top)
  if (/\/season$/.test(path)) return null;
  // the fixture list has its own title and actions
  if (active === "fixtures" && !/\/paper$/.test(path)) return <AreaSubNav />;
  return <AreaHeader />;
}

/** Header for org-level pages that sit in a destination for staff and stand alone for others. */
export function AreaOrPageHeader({ title }: { title: string }) {
  const { mode, dest, team } = useArea();
  if (mode === "staff" && (dest === "training" || (dest === "team" && team))) return <AreaHeader title={title} />;
  return <PageHeader title={title} />;
}

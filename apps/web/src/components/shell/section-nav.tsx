"use client";

import Link from "next/link";
import { ChevronLeft, Grid3x3, Sparkles } from "lucide-react";
import { buttonClass } from "@/components/ui/button";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { teamSectionOf, trainingSectionOf, videoWork } from "@/lib/nav-model";
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
                  "block whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
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

export function TeamHeader({ actions }: { actions?: ReactNode }) {
  const t = useTranslations("shell");
  const tr = useTranslations();
  const path = usePathname();
  const { org, team } = useShell();
  if (!team) return null;
  const base = `/app/${org.id}/teams/${team.id}`;
  const staff = videoWork(org.my_role, team.my_role);
  const items = [
    { key: "roster", href: base, label: t("roster") },
    { key: "season", href: `${base}/season`, label: t("season") },
    ...(staff ? [{ key: "library", href: `${base}/library`, label: t("library") }] : []),
  ];
  const section = teamSectionOf(path);
  const page: string = path.replace(/^\/app\/[^/]+(\/teams\/[^/]+)?/, "").split("/")[1] ?? "";
  const LEAF: Record<string, [string, string, string]> = {
    playlists: ["library", "library", "playlists"],
    plays: ["library", "library", "plays"],
    presentations: ["library", "library", "presentations"],
    search: ["library", "library", "search"],
  };
  const leaf = LEAF[page];
  const seasonTools =
    staff && section === "season" ? (
      <>
        <Link href={`${base}/matrix`} className={buttonClass("secondary", "sm")} aria-current={page === "matrix" ? "page" : undefined}>
          <Grid3x3 aria-hidden />
          {tr("palette.matrix")}
        </Link>
        <Link href={`${base}/assistant`} className={buttonClass("secondary", "sm")} aria-current={page === "assistant" ? "page" : undefined}>
          <Sparkles aria-hidden />
          {tr("palette.ask")}
        </Link>
      </>
    ) : null;
  return (
    <div className="space-y-5">
      <PageHeader eyebrow={team.season ?? org.name} title={team.name} actions={actions ?? seasonTools} />
      <SubNav label={t("teamSections")} items={items} active={section} />
      {leaf && <LeafTitle base={base} leaf={leaf} page={page} />}
    </div>
  );
}

function LeafTitle({ base, leaf, page }: { base: string; leaf: [string, string, string]; page: string }) {
  const t = useTranslations();
  const parentLabel = leaf[0] === "library" ? t("library.title") : t("shell.season");
  const title = page === "matrix" ? t("palette.matrix") : page === "assistant" ? t("palette.ask") : t(`library.${leaf[2]}` as "library.plays");
  const href = `${base}/${leaf[0] === "library" ? "library" : "season"}`;
  return (
    <div className="flex items-center gap-2 pt-2">
      <Link href={href} aria-label={t("library.back", { name: parentLabel })} className="grid size-8 place-items-center rounded-full text-muted ring-1 ring-border hover:bg-surface hover:text-foreground">
        <ChevronLeft aria-hidden className="size-4" />
      </Link>
      {page === "search" ? <span className="text-sm font-medium text-muted">{t("library.title")}</span> : <h2 className="text-xl font-bold">{title}</h2>}
    </div>
  );
}

export function TrainingHeader({ actions }: { actions?: ReactNode }) {
  const t = useTranslations("shell");
  const path = usePathname();
  const { org, team } = useShell();
  const base = `/app/${org.id}`;
  const teamBase = team ? `${base}/teams/${team.id}` : null;
  const items = [
    ...(teamBase ? [{ key: "plan", href: `${teamBase}/training`, label: t("plan") }] : []),
    { key: "dates", href: `${base}/schedule`, label: t("dates") },
    { key: "drills", href: `${base}/drills`, label: t("drills") },
    ...(teamBase ? [{ key: "assignments", href: `${teamBase}/assignments`, label: t("assignments") }] : []),
  ];
  return (
    <div className="space-y-5">
      <PageHeader eyebrow={team?.name} title={t("training")} actions={actions} />
      <SubNav label={t("trainingSections")} items={items} active={trainingSectionOf(path)} />
    </div>
  );
}

/** Team layout chrome: the team header on team pages, the training header on training pages. */
export function TeamChrome() {
  const path = usePathname();
  const { mode } = useShell();
  if (teamSectionOf(path)) return <TeamHeader />;
  if (mode === "staff" && trainingSectionOf(path)) return <TrainingHeader />;
  return null;
}

/** Header for pages that sit in Training for staff and stand alone for players (dates, drills). */
export function TrainingOrPageHeader({ title }: { title: string }) {
  const { mode } = useShell();
  if (mode === "staff") return <TrainingHeader />;
  return <PageHeader title={title} />;
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Search, X } from "lucide-react";
import { NotificationBell } from "@/components/training/bell";
import { destOf, modeFor, navFor, teamInPath } from "@/lib/nav-model";
import { cn } from "@/lib/utils";
import { AccountMenu } from "./account-menu";
import { ClubMark } from "./club-mark";
import { CommandPalette } from "./command-palette";
import { ShellContext, setCookie, TEAM_COOKIE, type ShellOrg, type ShellTeam, type ShellValue } from "./context";
import { DEST_ICON } from "./icons";
import { TeamSwitcher } from "./team-switcher";

export function AppShell({
  org,
  orgs,
  teams,
  me,
  savedTeam,
  banner,
  children,
}: {
  org: ShellOrg;
  orgs: { id: string; name: string }[];
  teams: ShellTeam[];
  me: { name: string; email: string };
  savedTeam: string | null;
  banner?: ReactNode;
  children: ReactNode;
}) {
  const t = useTranslations("shell");
  const path = usePathname();
  const [chosen, setChosen] = useState<string | null>(savedTeam);
  const urlTeam = teamInPath(path);
  const teamId = [urlTeam, chosen, teams[0]?.id].find((id) => id && teams.some((x) => x.id === id)) ?? null;
  const team = teams.find((x) => x.id === teamId) ?? null;
  const mode = modeFor(org.my_role, team?.my_role);
  const setTeam = useCallback((id: string) => {
    setChosen(id);
    setCookie(TEAM_COOKIE, id);
  }, []);
  useEffect(() => {
    if (urlTeam && urlTeam !== chosen) setTeam(urlTeam);
  }, [urlTeam]); // eslint-disable-line react-hooks/exhaustive-deps

  const value = useMemo<ShellValue>(() => ({ org, orgs, teams, team, mode, me, setTeam }), [org, orgs, teams, team, mode, me, setTeam]);
  const items = navFor(mode, org.id, team?.id ?? null);
  const active = destOf(path, mode);
  const [palette, setPalette] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // courtside and presentation tools use the whole screen, with one way back
  const tool = /\/(present|remote|live|marks)$/.test(path);
  if (tool) {
    const back = path.replace(/\/[^/]+$/, "");
    return (
      <ShellContext.Provider value={value}>
        <div className="flex min-h-dvh flex-col">
          <header className="flex items-center gap-3 px-3 py-2 sm:px-5">
            <Link href={back} aria-label={t("closeTool")} className="grid size-10 place-items-center rounded-full text-muted ring-1 ring-border hover:bg-surface hover:text-foreground">
              <X aria-hidden className="size-5" />
            </Link>
            <ClubMark org={org} className="size-7 rounded-lg" />
            <span className="min-w-0 truncate text-sm font-semibold">{team?.name ?? org.name}</span>
          </header>
          <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 pb-6 sm:px-5">
            {children}
          </main>
        </div>
      </ShellContext.Provider>
    );
  }

  return (
    <ShellContext.Provider value={value}>
      <>
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[70] focus:rounded-full focus:bg-raised focus:px-4 focus:py-2 focus:shadow-lg">
          {t("skip")}
        </a>
        <div className="min-h-dvh lg:grid lg:grid-cols-[16rem_1fr]">
          {/* desktop sidebar */}
          <aside className="sticky top-0 hidden h-dvh flex-col gap-6 border-r border-border/70 bg-background px-3 py-4 lg:flex">
            <div className="space-y-3 px-1">
              <Link href={`/app/${org.id}`} className="flex items-center gap-3 rounded-xl p-1 hover:bg-surface">
                <ClubMark org={org} />
                <span className="min-w-0 truncate font-semibold font-wide">{org.name}</span>
              </Link>
              <TeamSwitcher />
            </div>
            <nav aria-label={t("mainNav")} className="flex flex-col gap-0.5">
              {items.map((it) => {
                const Icon = DEST_ICON[it.key];
                const on = active === it.key;
                return (
                  <Link
                    key={it.key}
                    href={it.href}
                    aria-current={on ? "page" : undefined}
                    className={cn(
                      "group flex items-center gap-3 rounded-xl px-3 py-2 text-[0.9375rem] font-medium transition-colors",
                      on ? "bg-raised text-foreground shadow-sm ring-1 ring-border/70" : "text-muted hover:bg-surface hover:text-foreground",
                    )}
                  >
                    <Icon aria-hidden className={cn("size-[1.15rem]", on ? "text-accent" : "")} strokeWidth={on ? 2.2 : 1.8} />
                    {t(it.key)}
                  </Link>
                );
              })}
            </nav>
            <div className="mt-auto space-y-1">
              <button
                type="button"
                onClick={() => setPalette(true)}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-muted hover:bg-surface hover:text-foreground"
                data-testid="palette-open"
              >
                <Search aria-hidden className="size-4" />
                <span className="flex-1 text-left">{t("search")}</span>
                <kbd className="rounded-md bg-surface px-1.5 py-0.5 font-sans text-[0.6875rem] text-muted ring-1 ring-border">⌘K</kbd>
              </button>
              <div className="flex items-center gap-1 px-1">
                <AccountMenu />
                <NotificationBell orgId={org.id} />
              </div>
            </div>
          </aside>

          <div className="flex min-w-0 flex-col">
            {/* phone top bar */}
            <header className="sticky top-0 z-30 flex items-center gap-2 border-b border-border/70 bg-background/85 px-3 py-2 backdrop-blur-xl lg:hidden">
              <Link href={`/app/${org.id}`} aria-label={org.name} className="shrink-0">
                <ClubMark org={org} className="size-8 rounded-lg" />
              </Link>
              <div className="min-w-0 flex-1">
                <TeamSwitcher compact />
              </div>
              <button
                type="button"
                aria-label={t("search")}
                onClick={() => setPalette(true)}
                className="grid size-10 place-items-center rounded-full text-muted hover:bg-surface hover:text-foreground"
              >
                <Search aria-hidden className="size-5" />
              </button>
              <NotificationBell orgId={org.id} />
              <AccountMenu compact />
            </header>

            {banner}
            <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1240px] flex-1 px-4 pt-5 pb-28 outline-none sm:px-6 lg:px-10 lg:pt-10 lg:pb-16">
              {children}
            </main>
          </div>
        </div>

        {/* phone tab bar */}
        <nav
          aria-label={t("mainNav")}
          className="fixed inset-x-0 bottom-0 z-30 border-t border-border/70 bg-background/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
        >
          <ul className="mx-auto flex max-w-md">
            {items.map((it) => {
              const Icon = DEST_ICON[it.key];
              const on = active === it.key;
              return (
                <li key={it.key} className="flex-1">
                  <Link
                    href={it.href}
                    aria-current={on ? "page" : undefined}
                    className={cn("flex flex-col items-center gap-0.5 pt-2 pb-1.5 text-[0.6875rem] font-medium", on ? "text-accent" : "text-muted")}
                  >
                    <Icon aria-hidden className="size-6" strokeWidth={on ? 2.2 : 1.7} />
                    {t(it.key)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <CommandPalette open={palette} onOpenChange={setPalette} />
      </>
    </ShellContext.Provider>
  );
}

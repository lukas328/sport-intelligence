"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Plus, Search, X } from "lucide-react";
import { NotificationBell } from "@/components/training/bell";
import { destOf, modeFor, navFor, sectionOf, sectionsFor, startHref, teamInPath, uploadHref } from "@/lib/nav-model";
import { buttonClass } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AccountMenu } from "./account-menu";
import { ClubMark } from "./club-mark";
import { CommandPalette } from "./command-palette";
import { ShellContext, setCookie, TEAM_COOKIE, type ShellOrg, type ShellTeam, type ShellValue } from "./context";
import { DEST_ICON, IconUpload } from "./icons";
import { NextUp } from "./next-up";
import { TeamSwitcher } from "./team-switcher";

export function AppShell({
  org,
  orgs,
  teams,
  me,
  savedTeam,
  banner,
  clubVars,
  children,
}: {
  clubVars?: Record<string, string>;
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
  const navOpts = { teamFunctions: team?.team_features ?? false };
  const items = navFor(mode, org.id, team?.id ?? null, navOpts);
  const active = destOf(path, mode);
  const home = startHref(mode, org.id, team?.id ?? null);
  // one action reachable from everywhere for staff (SPEC section 6)
  const upload = mode === "staff" ? uploadHref(org.id, team?.id ?? null) : null;
  const [palette, setPalette] = useState(false);

  // menus and dialogs render at the end of <body>: give the document the club's colours too
  useEffect(() => {
    if (!clubVars) return;
    const root = document.documentElement;
    for (const [k, v] of Object.entries(clubVars)) root.style.setProperty(k, v);
    return () => {
      for (const k of Object.keys(clubVars)) root.style.removeProperty(k);
    };
  }, [clubVars]);

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
            <Link href={back} aria-label={t("closeTool")} className="grid size-10 place-items-center rounded-md text-muted ring-1 ring-border hover:bg-surface hover:text-foreground">
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
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[70] focus:rounded-md focus:bg-raised focus:px-4 focus:py-2 focus:shadow-lg">
          {t("skip")}
        </a>
        <div className="min-h-dvh lg:grid lg:grid-cols-[16rem_1fr]">
          {/* desktop sidebar: the club's deep colour, a dark island in every theme */}
          <aside className="on-deep sticky top-0 hidden h-dvh flex-col gap-7 bg-deep px-3 pt-5 pb-4 lg:flex">
            <div className="space-y-3 px-1">
              <Link href={home} className="flex items-center gap-3 rounded-md p-1 hover:bg-surface">
                <ClubMark org={org} />
                <span className="min-w-0 text-[1.375rem] leading-[1.05] font-display break-words">{org.name}</span>
              </Link>
              <TeamSwitcher />
              {upload && (
                <Link href={upload} className={buttonClass("primary", "md", "w-full")} data-testid="upload-video">
                  <IconUpload />
                  {t("upload")}
                </Link>
              )}
            </div>
            <nav aria-label={t("mainNav")} className="flex flex-col gap-0.5">
              {items.map((it) => {
                const Icon = DEST_ICON[it.key];
                const on = active === it.key;
                const subs = on ? sectionsFor(it.key, mode, org.id, team?.id ?? null, navOpts) : [];
                const subOn = sectionOf(path);
                const here = on && !subs.some((x) => x.key === subOn);
                return (
                  <div key={it.key}>
                    <Link
                      href={it.href}
                      aria-current={here ? "page" : undefined}
                      className={cn(
                        "flex min-h-11 items-center gap-3 rounded-md px-3 text-[0.9375rem] font-medium transition-colors",
                        on ? "text-foreground" : "text-muted hover:bg-surface hover:text-foreground",
                        here && "bg-surface shadow-[inset_3px_0_0_var(--mark)]",
                      )}
                    >
                      <Icon className="size-5 shrink-0" />
                      {t(it.key)}
                    </Link>
                    {subs.length > 0 && (
                      <ul className="mt-0.5 mb-1.5 space-y-0.5">
                        {subs.map((x) => (
                          <li key={x.key}>
                            <Link
                              href={x.href}
                              aria-current={x.key === subOn ? "page" : undefined}
                              className={cn(
                                "flex min-h-9 items-center rounded-md pr-2 pl-11 text-[0.9375rem] transition-colors",
                                x.key === subOn ? "bg-surface font-semibold text-foreground shadow-[inset_3px_0_0_var(--mark)]" : "text-muted hover:bg-surface hover:text-foreground",
                              )}
                            >
                              {t(x.key)}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </nav>
            <div className="mt-auto space-y-3">
              <NextUp />
              <button
                type="button"
                onClick={() => setPalette(true)}
                className="flex min-h-10 w-full items-center gap-3 rounded-md px-3 text-sm text-muted hover:bg-surface hover:text-foreground"
                data-testid="palette-open"
              >
                <Search aria-hidden className="size-4" />
                <span className="flex-1 text-left">{t("search")}</span>
                <kbd className="rounded-sm px-1.5 py-0.5 font-sans text-[0.6875rem] text-muted ring-1 ring-border">⌘K</kbd>
              </button>
              <div className="flex items-center gap-1 border-t border-border px-1 pt-3">
                <AccountMenu />
                <NotificationBell orgId={org.id} />
              </div>
            </div>
          </aside>

          <div className="flex min-w-0 flex-col overflow-x-clip">
            {/* phone top bar */}
            <header className="on-deep sticky top-0 z-30 flex items-center gap-2 bg-deep px-3 py-2 lg:hidden">
              <Link href={home} aria-label={org.name} className="shrink-0">
                <ClubMark org={org} className="size-8 rounded-md" />
              </Link>
              <div className="min-w-0 flex-1">
                <TeamSwitcher compact />
              </div>
              <button
                type="button"
                aria-label={t("search")}
                onClick={() => setPalette(true)}
                className="grid size-10 place-items-center rounded-md text-muted hover:bg-surface hover:text-foreground"
              >
                <Search aria-hidden className="size-5" />
              </button>
              {upload && (
                <Link href={upload} aria-label={t("upload")} className="grid size-10 place-items-center rounded-md text-muted ring-1 ring-border hover:bg-surface hover:text-foreground" data-testid="upload-video-compact">
                  <Plus aria-hidden className="size-5" />
                </Link>
              )}
              <NotificationBell orgId={org.id} />
              <AccountMenu compact />
            </header>

            {banner}
            <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1240px] flex-1 px-4 pt-5 pb-28 outline-none sm:px-6 lg:px-10 lg:pt-10 lg:pb-16">
              {/* a short rise on every page change: the new content is clearly new */}
              <div key={path} className="animate-rise">
                {children}
              </div>
            </main>
          </div>
        </div>

        {/* phone tab bar */}
        <nav aria-label={t("mainNav")} className="on-deep fixed inset-x-0 bottom-0 z-30 bg-deep pb-[env(safe-area-inset-bottom)] lg:hidden">
          <ul className="mx-auto flex max-w-md">
            {items.map((it) => {
              const Icon = DEST_ICON[it.key];
              const on = active === it.key;
              return (
                <li key={it.key} className="flex-1">
                  <Link
                    href={it.href}
                    aria-current={on ? "page" : undefined}
                    className={cn(
                      "flex flex-col items-center gap-1 pt-2.5 pb-2 text-xs font-medium",
                      on ? "text-foreground shadow-[inset_0_3px_0_var(--mark)]" : "text-muted",
                    )}
                  >
                    <Icon className="size-6" />
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

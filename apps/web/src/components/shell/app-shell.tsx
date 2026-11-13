"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ChevronLeft, Plus, Search } from "lucide-react";
import { NotificationBell } from "@/components/training/bell";
import { destOf, modeFor, navFor, startHref, teamInPath, uploadHref } from "@/lib/nav-model";
import { buttonClass } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AppMark } from "@/components/brand";
import { AccountMenu } from "./account-menu";
import { ClubMark } from "./club-mark";
import { CommandPalette } from "./command-palette";
import {
  ShellContext,
  setCookie,
  TEAM_COOKIE,
  type ShellOrg,
  type ShellTeam,
  type ShellValue,
} from "./context";
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
  me: { name: string; email: string; /** the club asks for two-factor and it is not set up */ two_factor_due?: boolean };
  savedTeam: string | null;
  banner?: ReactNode;
  children: ReactNode;
}) {
  const t = useTranslations("shell");
  const path = usePathname();
  const search = useSearchParams();
  const [chosen, setChosen] = useState<string | null>(savedTeam);
  const urlTeam = teamInPath(path);
  const teamId =
    [urlTeam, chosen, teams[0]?.id].find((id) => id && teams.some((x) => x.id === id)) ?? null;
  const team = teams.find((x) => x.id === teamId) ?? null;
  const mode = modeFor(org.my_role, team?.my_role);
  const setTeam = useCallback((id: string) => {
    setChosen(id);
    setCookie(TEAM_COOKIE, id);
  }, []);
  useEffect(() => {
    if (urlTeam && urlTeam !== chosen) setTeam(urlTeam);
  }, [urlTeam]); // eslint-disable-line react-hooks/exhaustive-deps

  const value = useMemo<ShellValue>(
    () => ({ org, orgs, teams, team, mode, me, setTeam }),
    [org, orgs, teams, team, mode, me, setTeam],
  );
  const navOpts = { teamFunctions: team?.team_features ?? false };
  const items = navFor(mode, org.id, team?.id ?? null, navOpts);
  const active = destOf(path, mode);
  const home = startHref(mode, org.id, team?.id ?? null);
  // one action reachable from everywhere for staff (SPEC section 6)
  const upload = mode === "staff" ? uploadHref(org.id, team?.id ?? null) : null;
  const [palette, setPalette] = useState(false);
  const searchHref = mode === "staff" && team ? `/app/${org.id}/teams/${team.id}/scenes?focus=1` : null;

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
  const tool = /\/(present|remote|live|marks|matchday|check)$/.test(path);
  // Prüfen and the Spieltag keys bring their own top line («Später weiter», «Beenden»)
  const ownTop = path.endsWith("/check") || (path.endsWith("/matchday") && search.get("mode") !== "detail");
  if (tool) {
    const back = path.replace(/\/[^/]+$/, "");
    return (
      <ShellContext.Provider value={value}>
        <div className="flex min-h-dvh flex-col">
          {!ownTop && (
            <header className="flex h-[60px] items-center gap-3 border-b-2 border-ink px-4 md:px-8">
              <Link
                href={back}
                className="flex min-h-11 flex-1 items-center gap-1.5 text-[15px] font-bold"
                aria-label={t("closeTool")}
              >
                <ChevronLeft aria-hidden className="size-5" />
                {team?.name ?? org.name}
              </Link>
            </header>
          )}
          <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 pb-6 md:px-8">
            {children}
          </main>
        </div>
      </ShellContext.Provider>
    );
  }

  const navLink = (on: boolean) =>
    cn(
      "font-slant relative flex items-center text-ink-2 no-underline hover:text-ink",
      on && "text-ink",
    );

  return (
    <ShellContext.Provider value={value}>
      <>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[70] focus:bg-paper focus:px-4 focus:py-2 focus:outline-3 focus:outline-ink"
        >
          {t("skip")}
        </a>
        <div className="flex min-h-dvh flex-col">
          {/* the frame (Anlauf): crest and club, four destinations, search and the one action */}
          <header className="cloth sticky top-0 z-30 border-b-2 border-ink" data-frame="top">
            <div className="mx-auto hidden h-16 max-w-[1440px] items-center gap-5 px-8 lg:flex">
              <Link
                href={home}
                className="font-slant flex shrink-0 items-center gap-3 text-xl leading-none whitespace-nowrap text-ink no-underline"
              >
                {/* the product in ink, then the club: the colours belong to the club */}
                <AppMark size={32} />
                <ClubMark org={org} />
                {org.name}
              </Link>
              <div className="max-w-40 min-w-0 shrink">
                <TeamSwitcher compact />
              </div>
              <nav aria-label={t("mainNav")} className="flex self-stretch">
                {items.map((it) => {
                  const on = active === it.key;
                  return (
                    <Link
                      key={it.key}
                      href={it.href}
                      aria-current={on ? "page" : undefined}
                      className={cn(navLink(on), "px-3.5 text-lg")}
                    >
                      {t(it.key)}
                      {on && (
                        <span
                          aria-hidden
                          data-mark=""
                          className="mark-band absolute right-2.5 -bottom-0.5 left-2.5 h-1.5"
                        />
                      )}
                    </Link>
                  );
                })}
              </nav>
              <div className="ml-auto flex items-center gap-4">
                {/* «Suchen» is the scene search (SPEC 9); the palette stays on Ctrl+K */}
                {searchHref ? (
                  <Link href={searchHref} className="min-h-11 content-center font-bold text-ink underline decoration-[1.5px] underline-offset-4" data-testid="search-open">
                    {t("search")}
                  </Link>
                ) : (
                  <button
                    type="button"
                    onClick={() => setPalette(true)}
                    className="min-h-11 cursor-pointer font-bold underline decoration-[1.5px] underline-offset-4"
                    data-testid="palette-open"
                  >
                    {t("search")}
                  </button>
                )}
                {upload && (
                  <Link
                    href={upload}
                    className={buttonClass("primary", "md")}
                    data-testid="upload-video"
                  >
                    {t("upload")}
                  </Link>
                )}
                <NotificationBell orgId={org.id} />
                <AccountMenu compact />
              </div>
            </div>
            {/* phone top bar (UX test H06, H09): the crest, the team name kept also with large
                text, the bell, «Suchen» and «Video» with their words, the account */}
            <div className="flex h-[60px] items-center gap-2 px-4 lg:hidden">
              {/* with large text the crest gives way, the team name stays (UX test H09) */}
              <Link href={home} aria-label={org.name} className="flex shrink-0 items-center max-[359px]:hidden">
                <ClubMark org={org} className="h-[34px] w-[30px] text-[14px]" />
              </Link>
              <div className="min-w-0 flex-1">
                <TeamSwitcher compact />
              </div>
              <NotificationBell orgId={org.id} />
              {/* «Suchen» with its word on the phone too (SPEC 6, UX test B18/N08) */}
              {searchHref && (
                <Link href={searchHref} className="flex h-11 min-w-11 shrink-0 items-center justify-center gap-1 text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4" data-testid="search-open-compact">
                  <Search aria-hidden className="size-4 max-[439px]:size-5" strokeWidth={2.6} />
                  {/* with very large text the word gives way to the team name, the magnifier stays */}
                  <span className="max-[439px]:sr-only">{t("search")}</span>
                </Link>
              )}
              {upload && (
                <Link
                  href={upload}
                  className="flex h-11 shrink-0 items-center gap-1 border-2 border-ink bg-ink px-2.5 text-[15px] font-bold text-ground no-underline"
                  data-testid="upload-video-compact"
                >
                  <Plus aria-hidden className="size-4" strokeWidth={2.6} />
                  {t("uploadShort")}
                </Link>
              )}
              <AccountMenu compact />
            </div>
          </header>

          {banner}
          <main
            id="main"
            tabIndex={-1}
            className="mx-auto w-full max-w-[1440px] flex-1 px-4 pt-6 pb-28 outline-none md:px-8 lg:pt-8 lg:pb-16"
          >
            {/* a short rise on every page change: the new content is clearly new */}
            <div key={path} className="animate-rise">
              {children}
            </div>
          </main>
        </div>

        {/* phone tab bar: the four destinations, the active one with the club band on top */}
        <nav
          aria-label={t("mainNav")}
          className="cloth fixed inset-x-0 bottom-0 z-30 border-t-2 border-ink pb-[env(safe-area-inset-bottom)] lg:hidden"
          data-frame="tabbar"
        >
          <ul
            className="mx-auto grid max-w-md"
            style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
          >
            {items.map((it) => {
              const on = active === it.key;
              return (
                <li key={it.key}>
                  <Link
                    // Szenen on the phone opens with the cursor in the search (UX test B18/N08)
                    href={it.key === "scenes" && searchHref ? searchHref : it.href}
                    aria-current={on ? "page" : undefined}
                    className={cn(navLink(on), "min-h-14 justify-center text-base")}
                  >
                    {on && (
                      <span
                        aria-hidden
                        data-mark=""
                        className="mark-band absolute -top-0.5 right-[18px] left-[18px] h-1.5"
                      />
                    )}
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

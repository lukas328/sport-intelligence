"use client";

import { Check, ChevronsUpDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { MenuContent, MenuItem, MenuLabel, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { cn } from "@/lib/utils";
import { useShell } from "./context";

/** Active team (and club, for people in several clubs). Every team-scoped page follows it. */
export function TeamSwitcher({ compact }: { compact?: boolean }) {
  const t = useTranslations();
  const { teams, team, org, orgs, setTeam } = useShell();
  const router = useRouter();
  const label = team ? team.name : t("shell.noTeam");
  const sub = team?.season ?? null;
  if (teams.length <= 1 && orgs.length <= 1) {
    return (
      <div className={cn("min-w-0", compact ? "px-1" : "px-2")}>
        <p className={cn("font-semibold", compact ? "line-clamp-2 text-[15px] leading-tight break-words" : "truncate text-sm")}>{label}</p>
        {sub && !compact && <p className="truncate text-xs text-muted">{sub}</p>}
      </div>
    );
  }
  return (
    <MenuRoot>
      <MenuTrigger
        className={cn(
          "flex min-h-11 w-full min-w-0 items-center gap-2 text-left hover:bg-surface",
          compact ? "px-1 py-1" : "px-2 py-1.5 border border-border",
        )}
        aria-label={`${t("shell.switchTeam")}: ${label}`}
        data-testid="team-switcher"
      >
        <span className="min-w-0 flex-1">
          {/* on the phone two lines rather than «H…» (UX test H09) */}
          <span className={cn("block font-semibold", compact ? "line-clamp-2 text-[15px] leading-tight break-words" : "truncate text-sm")}>{label}</span>
          {sub && !compact && <span className="block truncate text-xs text-muted">{sub}</span>}
        </span>
        <ChevronsUpDown aria-hidden className="size-4 shrink-0 text-muted" />
      </MenuTrigger>
      <MenuContent align="start" className="w-72">
        <MenuLabel>{t("palette.teams")}</MenuLabel>
        {teams.map((x) => (
          <MenuItem
            key={x.id}
            icon={x.id === team?.id ? <Check className="!text-accent" /> : <span className="size-4" />}
            onSelect={() => {
              setTeam(x.id);
              // stay on the same kind of page for the new team
              const here = window.location.pathname;
              // a page of one match or collection belongs to the old team: go to the new team's
              // matches (UX test B30)
              const own = /\/app\/[^/]+\/(matches|collections|opponents|playlists|presentations)\//.test(here);
              router.push(team && here.includes(`/teams/${team.id}`) ? here.replace(team.id, x.id) : own ? `/app/${org.id}/teams/${x.id}/matches` : here);
              router.refresh();
            }}
          >
            {x.name}
          </MenuItem>
        ))}
        {orgs.length > 1 && (
          <>
            <MenuSeparator />
            <MenuLabel>{t("shell.otherClubs")}</MenuLabel>
            {orgs
              .filter((o) => o.id !== org.id)
              .map((o) => (
                <MenuItem key={o.id} href={`/app/${o.id}`} icon={<span className="size-4" />}>
                  {o.name}
                </MenuItem>
              ))}
          </>
        )}
      </MenuContent>
    </MenuRoot>
  );
}

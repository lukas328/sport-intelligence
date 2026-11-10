"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, HelpCircle, LogOut, MessageSquare, Monitor, Moon, Settings, ShieldCheck, Sun, UserRound } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { FeedbackDialog } from "@/components/support/support-bar";
import { helpUrl } from "@/components/support/help-map";
import { MenuContent, MenuItem, MenuLabel, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import { setCookie, THEME_COOKIE, useShell } from "./context";

type Theme = "system" | "light" | "dark";

function currentTheme(): Theme {
  const v = document.documentElement.dataset.theme;
  return v === "light" || v === "dark" ? v : "system";
}

export function applyTheme(theme: Theme) {
  if (theme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = theme;
  setCookie(THEME_COOKIE, theme);
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
}

export function AccountMenu({ compact }: { compact?: boolean }) {
  const t = useTranslations("shell");
  const tc = useTranslations("common");
  const { org, me, team, teams } = useShell();
  // "Verein" for admins and coaches (lib/settings-model.ts); own consents with "Teamfunktionen"
  const club = org.my_role === "org_admin" || teams.some((x) => x.my_role === "coach");
  const consents = team?.team_features ?? false;
  const router = useRouter();
  const locale = useLocale();
  const path = usePathname();
  const [theme, setTheme] = useState<Theme>("system");
  const [feedback, setFeedback] = useState(false);
  useEffect(() => setTheme(currentTheme()), []);
  const cfg = useQuery({ queryKey: ["support-config"], queryFn: async () => (await api.GET("/v1/support/config")).data ?? null, staleTime: 3_600_000 });
  const base = `/app/${org.id}`;
  const themes: [Theme, typeof Sun][] = [
    ["system", Monitor],
    ["light", Sun],
    ["dark", Moon],
  ];
  return (
    <>
      <MenuRoot>
        <MenuTrigger
          aria-label={`${t("account")}: ${me.name}`}
          data-testid="account-menu"
          className={cn(
            "flex min-w-0 items-center gap-3 rounded-md text-left hover:bg-surface",
            compact ? "p-1" : "flex-1 px-2 py-1.5",
          )}
        >
          <span aria-hidden className="grid size-8 shrink-0 place-items-center rounded-full bg-foreground text-[0.75rem] font-semibold text-background font-wide">
            {initials(me.name) || "?"}
          </span>
          {!compact && (
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium">{me.name}</span>
              <span className="block truncate text-xs text-muted">{me.email}</span>
            </span>
          )}
        </MenuTrigger>
        <MenuContent align={compact ? "end" : "start"} side={compact ? "bottom" : "top"} className="w-64">
          <MenuItem href={`${base}/me`} icon={<UserRound />} testId="menu-me">
            {t("me")}
          </MenuItem>
          {club && (
            <MenuItem href={`${base}/club`} icon={<Settings />} testId="menu-settings">
              {t("club")}
            </MenuItem>
          )}
          {consents && (
            <MenuItem href={`${base}/consents`} icon={<ShieldCheck />}>
              {t("consents")}
            </MenuItem>
          )}
          <MenuSeparator />
          <MenuLabel>{t("appearance")}</MenuLabel>
          {themes.map(([k, Icon]) => (
            <MenuItem
              key={k}
              icon={<Icon />}
              onSelect={() => {
                applyTheme(k);
                setTheme(k);
              }}
            >
              <span className="flex items-center justify-between gap-2">
                {t(`theme_${k}`)}
                {theme === k && <Check aria-hidden className="!text-accent" />}
              </span>
            </MenuItem>
          ))}
          <MenuSeparator />
          <MenuItem href={helpUrl(cfg.data?.help_url ?? "https://handball-ai.ch/hilfe", locale, path)} external icon={<HelpCircle />} testId="help-link">
            {t("help")}
          </MenuItem>
          <MenuItem onSelect={() => setFeedback(true)} icon={<MessageSquare />}>
            {t("feedback")}
          </MenuItem>
          <MenuSeparator />
          <MenuItem
            icon={<LogOut />}
            onSelect={async () => {
              await api.POST("/v1/auth/logout");
              router.push("/login");
              router.refresh();
            }}
          >
            {tc("logout")}
          </MenuItem>
        </MenuContent>
      </MenuRoot>
      <FeedbackDialog orgId={org.id} open={feedback} onOpenChange={setFeedback} chat={cfg.data?.chat ?? null} />
    </>
  );
}

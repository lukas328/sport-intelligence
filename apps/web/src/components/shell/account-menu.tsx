"use client";

import { useQuery } from "@tanstack/react-query";
import { HelpCircle, Languages, LogOut, MessageSquare, Settings, ShieldAlert, ShieldCheck, UserRound } from "lucide-react";
import { LANGUAGE_NAMES, setLanguage } from "@/components/language-switch";
import { locales } from "@/i18n/config";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { FeedbackDialog } from "@/components/support/support-bar";
import { helpUrl } from "@/components/support/help-map";
import { MenuContent, MenuItem, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import { useShell } from "./context";
import { useTwoFactorReminder } from "./two-factor-reminder";

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
  const [feedback, setFeedback] = useState(false);
  const cfg = useQuery({ queryKey: ["support-config"], queryFn: async () => (await api.GET("/v1/support/config")).data ?? null, staleTime: 3_600_000 });
  const base = `/app/${org.id}`;
  const reminder = useTwoFactorReminder();
  return (
    <>
      <MenuRoot>
        <MenuTrigger
          aria-label={`${t("account")}: ${me.name}`}
          data-testid="account-menu"
          className={cn(
            "flex min-h-11 min-w-11 cursor-pointer items-center justify-center gap-3 text-left",
            !compact && "flex-1 px-2 py-1.5",
          )}
        >
          <span aria-hidden className="font-slant relative grid size-9 shrink-0 place-items-center bg-ink text-[13px] text-ground">
            {initials(me.name) || "?"}
            {reminder.due && <span className="absolute -top-1 -right-1 size-3 border-2 border-ground bg-error" data-testid="account-dot" />}
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
          {reminder.due && (
            <>
              <MenuItem href={`${base}/me/security`} icon={<ShieldAlert />} testId="menu-two-factor">
                {t("twoFactorDue")}
              </MenuItem>
              <MenuItem onSelect={reminder.later} icon={<span className="size-4" />} testId="menu-two-factor-later">
                {t("twoFactorLater")}
              </MenuItem>
            </>
          )}
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
          <MenuItem href={helpUrl(cfg.data?.help_url ?? "https://handball-ai.ch/hilfe", locale, path)} external icon={<HelpCircle />} testId="help-link">
            {t("help")}
          </MenuItem>
          <MenuItem onSelect={() => setFeedback(true)} icon={<MessageSquare />}>
            {t("feedback")}
          </MenuItem>
          <MenuSeparator />
          {/* the language, written out (UX test B06) */}
          {locales.map((l) => (
            <MenuItem
              key={l}
              icon={<Languages />}
              onSelect={() => {
                setLanguage(l);
                router.refresh();
              }}
              testId={`lang-${l}`}
            >
              <span lang={l} className={l === locale ? "font-bold underline decoration-[1.5px] underline-offset-4" : undefined} aria-current={l === locale ? "true" : undefined}>
                {LANGUAGE_NAMES[l]}
              </span>
            </MenuItem>
          ))}
          <MenuSeparator />
          <MenuItem
            icon={<LogOut />}
            onSelect={async () => {
              await api.POST("/v1/auth/logout");
              // the sign-in page says it (UX test B54)
              router.push("/login?out=1");
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

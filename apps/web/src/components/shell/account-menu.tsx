"use client";

import * as M from "@radix-ui/react-dropdown-menu";
import { useQuery } from "@tanstack/react-query";
import { Building2, HelpCircle, LogOut, MessageSquare, ShieldAlert, UserRound } from "lucide-react";
import Link from "next/link";
import { LANGUAGE_NAMES, setLanguage } from "@/components/language-switch";
import { locales } from "@/i18n/config";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { FeedbackDialog } from "@/components/support/support-bar";
import { helpUrl } from "@/components/support/help-map";
import { MenuContent, MenuItem, MenuLabel, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { api } from "@/lib/client";
import { coachRights } from "@/lib/roles";
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

/**
 * The account (finding K4): the person on top, then four clear groups, Ich, Verein, Hilfe and
 * Abmelden. The two-factor reminder is one compact card with «Einrichten» and «Später»; the dot on
 * the initials appears only when something is really blocked (two-factor overdue for an admin).
 */
export function AccountMenu({ compact }: { compact?: boolean }) {
  const t = useTranslations("shell");
  const tc = useTranslations("common");
  const { org, me, teams } = useShell();
  // «Verein» for the club's admins and the coaches of a team (lib/settings-model.ts)
  const club = org.my_role === "org_admin" || teams.some((x) => coachRights(org.my_role, x.my_role));
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
          aria-label={`${t("account")}: ${me.name}${reminder.overdue ? `, ${t("twoFactorDue")}` : ""}`}
          data-testid="account-menu"
          className={cn(
            "flex min-h-11 min-w-11 cursor-pointer items-center justify-center gap-3 text-left",
            !compact && "flex-1 px-2 py-1.5",
          )}
        >
          <span aria-hidden className="font-slant relative grid size-9 shrink-0 place-items-center bg-ink text-[15px] text-ground">
            {initials(me.name) || "?"}
            {reminder.overdue && <span className="absolute -top-1 -right-1 size-3 border-2 border-ground bg-error" data-testid="account-dot" />}
          </span>
          {!compact && (
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium">{me.name}</span>
              <span className="block truncate text-xs text-muted">{me.email}</span>
            </span>
          )}
        </MenuTrigger>
        <MenuContent align={compact ? "end" : "start"} side={compact ? "bottom" : "top"} className="w-72">
          {/* who is signed in: not an item, just the person */}
          <div className="px-3 pt-2 pb-2.5" data-testid="menu-person">
            <p className="m-0 truncate text-[15px] font-bold">{me.name}</p>
            <p className="m-0 truncate text-[14px] text-ink-2">{me.email}</p>
          </div>
          {reminder.due && (
            <div className="mx-1 mb-1.5 border-l-4 border-attn bg-surface px-3 py-2.5" data-testid="menu-two-factor-card">
              <p className="m-0 flex items-center gap-2 text-[15px] font-bold">
                <ShieldAlert aria-hidden className="size-4 shrink-0" />
                {t("twoFactorTitle")}
              </p>
              <p className="mt-1 mb-2 text-[14px] leading-snug text-ink-2">{reminder.overdue ? t("twoFactorOverdue") : t("twoFactorShort")}</p>
              <div className="flex flex-wrap gap-2">
                <M.Item asChild>
                  <Link
                    href={`${base}/me/security`}
                    className="inline-flex min-h-9 cursor-pointer items-center bg-ink px-3 text-[14px] font-bold text-ground no-underline outline-none data-[highlighted]:outline-2 data-[highlighted]:outline-offset-2 data-[highlighted]:outline-ink"
                    data-testid="menu-two-factor"
                  >
                    {t("twoFactorSetUp")}
                  </Link>
                </M.Item>
                {!reminder.overdue && (
                  <M.Item
                    onSelect={reminder.later}
                    className="inline-flex min-h-9 cursor-pointer items-center border-2 border-ink px-3 text-[14px] font-bold outline-none select-none data-[highlighted]:bg-raised"
                    data-testid="menu-two-factor-later"
                  >
                    {t("twoFactorLaterShort")}
                  </M.Item>
                )}
              </div>
            </div>
          )}
          <MenuSeparator />
          <MenuLabel>{t("groupMe")}</MenuLabel>
          <MenuItem href={`${base}/me`} icon={<UserRound />} testId="menu-me">
            {t("meItem")}
          </MenuItem>
          {/* the language, written out (UX test B06): one row of three */}
          <div role="group" aria-label={t("language")} className="flex items-center gap-1 px-2 pb-1">
            {locales.map((l) => (
              <M.Item
                key={l}
                onSelect={() => {
                  setLanguage(l);
                  router.refresh();
                }}
                data-testid={`lang-${l}`}
                className={cn(
                  "min-h-9 flex-1 cursor-pointer px-1.5 text-center text-[14px] leading-9 outline-none select-none data-[highlighted]:bg-surface",
                  l === locale && "font-bold underline decoration-[1.5px] underline-offset-4",
                )}
              >
                <span lang={l} aria-current={l === locale ? "true" : undefined}>
                  {LANGUAGE_NAMES[l]}
                </span>
              </M.Item>
            ))}
          </div>
          {club && (
            <>
              <MenuSeparator />
              <MenuLabel>{t("groupClub")}</MenuLabel>
              <MenuItem href={`${base}/club`} icon={<Building2 />} testId="menu-settings">
                {t("clubItem", { club: org.name })}
              </MenuItem>
            </>
          )}
          <MenuSeparator />
          <MenuLabel>{t("help")}</MenuLabel>
          <MenuItem href={helpUrl(cfg.data?.help_url ?? "https://handball-intelligence.com/hilfe", locale, path)} external icon={<HelpCircle />} testId="help-link">
            {t("helpItem")}
          </MenuItem>
          <MenuItem onSelect={() => setFeedback(true)} icon={<MessageSquare />}>
            {t("feedback")}
          </MenuItem>
          <MenuSeparator />
          <MenuItem
            icon={<LogOut />}
            testId="menu-logout"
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

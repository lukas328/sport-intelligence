"use client";

import * as D from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { Command } from "cmdk";
import {
  ArrowRight,
  BookOpen,
  Camera,
  Clapperboard,
  MessageCircleQuestion,
  Plus,
  ScanSearch,
  Settings,
  Upload,
  UserRound,
  Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { api } from "@/lib/client";
import { navFor, videoWork } from "@/lib/nav-model";
import { useShell } from "./context";
import { DEST_ICON } from "./icons";

const item =
  "flex cursor-pointer items-center gap-3 px-3 py-2.5 text-sm outline-none data-[selected=true]:bg-surface [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-muted";
const group = "px-1.5 [&_[cmdk-group-heading]]:eyebrow [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:pb-1";

/** ⌘K: jump anywhere, switch team, find a match, ask the data. */
export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const t = useTranslations();
  const format = useFormatter();
  const router = useRouter();
  const { org, team, teams, mode, setTeam } = useShell();
  const [q, setQ] = useState("");
  const staff = videoWork(org.my_role, team?.my_role);
  const base = `/app/${org.id}`;
  const teamBase = team ? `${base}/teams/${team.id}` : null;
  const matches = useQuery({
    queryKey: ["palette-matches", team?.id],
    enabled: open && Boolean(team),
    staleTime: 60_000,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { path: { org_id: org.id, team_id: team!.id } } })).data ?? [],
  });

  function go(href: string) {
    onOpenChange(false);
    setQ("");
    router.push(href);
  }

  const row = (key: string, label: string, icon: ReactNode, href: string, keywords: string[] = []) => (
    <Command.Item key={key} value={`${label} ${keywords.join(" ")}`} onSelect={() => go(href)} className={item}>
      {icon}
      <span className="flex-1 truncate">{label}</span>
    </Command.Item>
  );

  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-50 bg-[var(--overlay)] animate-fade" />
        <D.Content className="club fixed inset-x-3 top-[12dvh] z-50 mx-auto max-w-xl overflow-hidden bg-raised ring-1 ring-border animate-rise">
          <D.Title className="sr-only">{t("palette.title")}</D.Title>
          <D.Description className="sr-only">{t("palette.placeholder")}</D.Description>
          <Command label={t("palette.title")} loop>
            <Command.Input
              value={q}
              onValueChange={setQ}
              placeholder={t("palette.placeholder")}
              className="w-full border-b border-border/70 bg-transparent px-5 py-4 text-base outline-none placeholder:text-muted"
            />
            <Command.List className="max-h-[min(60dvh,26rem)] overflow-y-auto pb-2">
              <Command.Empty className="px-5 py-8 text-center text-sm text-muted">{t("palette.empty")}</Command.Empty>
              {staff && teamBase && q.trim().length > 2 && (
                <Command.Group heading={t("palette.ask")} className={group} forceMount>
                  <Command.Item
                    value={`ask ${q}`}
                    forceMount
                    onSelect={() => go(`${teamBase}/scenes?q=${encodeURIComponent(q.trim())}`)}
                    className={item}
                  >
                    <MessageCircleQuestion />
                    <span className="flex-1 truncate">{t("palette.askWith", { q: q.trim() })}</span>
                    <ArrowRight />
                  </Command.Item>
                </Command.Group>
              )}
              <Command.Group heading={t("palette.go")} className={group}>
                {navFor(mode, org.id, team?.id ?? null, { teamFunctions: team?.team_features ?? false }).map((it) => {
                  const Icon = DEST_ICON[it.key];
                  return row(it.key, t(`shell.${it.key}`), <Icon />, it.href);
                })}
                {teamBase && staff && row("collections", t("shell.collections"), <BookOpen />, `${teamBase}/collections`, ["playlists", "präsentationen", "presentations", "sammlung"])}
                {teamBase && staff && row("plays", t("shell.plays"), <BookOpen />, `${teamBase}/plays`, ["spielzüge", "taktik", "tactics"])}
                {row("me", t("shell.me"), <UserRound />, `${base}/me`, ["profil", "profile", "passwort", "password"])}
                {(org.my_role === "org_admin" || teams.some((x) => x.my_role === "coach")) &&
                  row("club", t("shell.club"), <Settings />, `${base}/club`, ["einstellungen", "settings", "teamfunktionen"])}
              </Command.Group>
              {staff && teamBase && (
                <Command.Group heading={t("palette.actions")} className={group}>
                  {row("upload", t("shell.upload"), <Upload />, `${teamBase}/matches?upload=1`, ["video"])}
                  {row("new-match", t("palette.newMatch"), <Plus />, `${teamBase}/matches?new=1`)}
                  {row("search", t("palette.searchScenes"), <ScanSearch />, `${teamBase}/scenes`)}
                  {row("paper", t("palette.paper"), <Camera />, `${teamBase}/matches?report=1`)}
                </Command.Group>
              )}
              {(matches.data ?? []).length > 0 && (
                <Command.Group heading={t("palette.matches")} className={group}>
                  {(matches.data ?? []).slice(0, 40).map((m) => {
                    const when = format.dateTime(new Date(m.kickoff_at), { day: "numeric", month: "short", year: "2-digit" });
                    const score = m.score_own != null && m.score_opponent != null ? `${m.score_own}:${m.score_opponent}` : "";
                    return (
                      <Command.Item key={m.id} value={`match ${m.opponent_name} ${when} ${m.competition ?? ""}`} onSelect={() => go(`${base}/matches/${m.id}`)} className={item}>
                        <Clapperboard />
                        <span className="flex-1 truncate">{m.opponent_name || t("matches.training")}</span>
                        <span className="text-xs text-muted tabular-nums">
                          {score && <span className="mr-2 font-semibold text-foreground">{score}</span>}
                          {when}
                        </span>
                      </Command.Item>
                    );
                  })}
                </Command.Group>
              )}
              {teams.length > 1 && (
                <Command.Group heading={t("palette.teams")} className={group}>
                  {teams.map((x) => (
                    <Command.Item
                      key={x.id}
                      value={`team ${x.name}`}
                      onSelect={() => {
                        setTeam(x.id);
                        go(`${base}/teams/${x.id}`);
                      }}
                      className={item}
                    >
                      <Users />
                      <span className="flex-1 truncate">{x.name}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
            </Command.List>
          </Command>
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}

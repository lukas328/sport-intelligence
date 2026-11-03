"use client";

import type { Schemas } from "@handball/api-client";
import { Camera, ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { PageHeader } from "@/components/ui/page-header";
import { matchState } from "@/lib/match-state";
import { cn } from "@/lib/utils";
import { NewMatchForm } from "./new-match-form";
import { PaperImport } from "./paper-import";

type Match = Schemas["MatchSummary"];

export function MatchesView({ orgId, teamId, matches, canWrite }: { orgId: string; teamId: string; matches: Match[]; canWrite: boolean }) {
  const t = useTranslations();
  const params = useSearchParams();
  const router = useRouter();
  const [open, setOpen] = useState(params.get("new") === "1");
  // kept here: the import refreshes the list, which swaps the layout below
  const [warnings, setWarnings] = useState<string[]>([]);
  const notice = warnings.length > 0 && (
    <Alert kind="info">
      <p className="font-medium">
        {t("paper.done")} {t("paper.warnings")}:
      </p>
      <ul className="list-disc pl-5">
        {warnings.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
    </Alert>
  );
  const now = useNow({ updateInterval: 60_000 });
  const upcoming = matches.filter((m) => new Date(m.kickoff_at) > now && m.score_own == null).sort((a, b) => a.kickoff_at.localeCompare(b.kickoff_at));
  const played = matches.filter((m) => !upcoming.includes(m)).sort((a, b) => b.kickoff_at.localeCompare(a.kickoff_at));
  const extra = canWrite && (
    <p className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted">
      <Link href={`/app/${orgId}/teams/${teamId}/paper`} className="inline-flex items-center gap-1.5 font-medium text-foreground hover:text-accent">
        <Camera aria-hidden className="size-4" />
        {t("matches.photoSheet")}
      </Link>
      <PaperImport orgId={orgId} teamId={teamId} onWarnings={setWarnings} />
    </p>
  );

  if (matches.length === 0) {
    return (
      <div className="space-y-8">
        <PageHeader title={t("matches.title")} />
        {notice}
        <p className="sr-only">{t("matches.empty")}</p>
        {canWrite ? (
          <div className="grid gap-8 lg:grid-cols-[1fr_20rem]">
            <Card className="sm:p-8">
              <h2 className="text-xl font-bold">{t("matches.emptyTitle")}</h2>
              <p className="mt-1 mb-6 text-sm text-muted">{t("matches.emptyHint")}</p>
              <NewMatchForm orgId={orgId} teamId={teamId} />
            </Card>
            <div className="space-y-3 lg:pt-8">
              <p className="text-sm text-muted">{t("matches.otherWays")}</p>
              {extra}
            </div>
          </div>
        ) : (
          <Card className="text-center text-muted">{t("matches.empty")}</Card>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <PageHeader
        title={t("matches.title")}
        actions={
          canWrite && (
            <Dialog
              open={open}
              onOpenChange={(o) => {
                setOpen(o);
                if (!o && params.get("new")) router.replace(`/app/${orgId}/teams/${teamId}/matches`);
              }}
              title={t("matches.new")}
              wide
              trigger={
                <Button data-testid="new-match">
                  <Plus aria-hidden />
                  {t("matches.newShort")}
                </Button>
              }
            >
              <NewMatchForm orgId={orgId} teamId={teamId} />
            </Dialog>
          )
        }
      />
      {canWrite && <div className="-mt-6">{extra}</div>}
      {notice}
      {upcoming.length > 0 && <MatchList title={t("matches.upcoming")} orgId={orgId} matches={upcoming} />}
      {played.length > 0 && <MatchList title={t("matches.played")} orgId={orgId} matches={played} />}
    </div>
  );
}

function MatchList({ title, orgId, matches }: { title: string; orgId: string; matches: Match[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-2xl">{title}</h2>
      <ul className="overflow-hidden rounded-lg border border-foreground/20 bg-raised" data-testid="match-list">
        {matches.map((m, i) => (
          <li key={m.id} className={cn(i > 0 && "border-t border-foreground/10")}>
            <MatchRow orgId={orgId} m={m} />
          </li>
        ))}
      </ul>
    </section>
  );
}

/** One line of the fixture list: when, where, against whom, how it stands, how it ended. */
export function MatchRow({ orgId, m }: { orgId: string; m: Match }) {
  const t = useTranslations();
  const format = useFormatter();
  const date = new Date(m.kickoff_at);
  const state = matchState(m);
  const result = m.score_own == null || m.score_opponent == null ? null : m.score_own > m.score_opponent ? "won" : m.score_own < m.score_opponent ? "lost" : "draw";
  return (
    <Link href={`/app/${orgId}/matches/${m.id}`} className="group grid grid-cols-[3.25rem_minmax(0,1fr)_auto] items-center gap-x-4 px-4 py-3.5 transition-colors hover:bg-surface sm:grid-cols-[4.5rem_minmax(0,1fr)_auto_auto] sm:px-5">
      <span className="leading-none">
        <span className="block font-display text-sm text-muted">{format.dateTime(date, { weekday: "short" })}</span>
        <span className="mt-0.5 block font-score text-2xl">{format.dateTime(date, { day: "2-digit", month: "2-digit" })}</span>
      </span>
      <span className="min-w-0">
        <span className="flex items-center gap-2">
          {m.kind !== "training" && (
            <span className="shrink-0 rounded-sm bg-surface px-1.5 py-px text-[0.6875rem] font-bold text-muted" title={m.is_home ? t("matches.homeShort") : t("matches.awayShort")}>
              {m.is_home ? t("matches.homeShort") : t("matches.awayShort")}
            </span>
          )}
          <span className="truncate text-[1.0625rem] font-semibold group-hover:text-accent">{m.kind === "training" ? t("matches.training") : m.opponent_name}</span>
        </span>
        <span className="mt-0.5 block truncate text-sm text-muted">
          {[m.competition, format.dateTime(date, { hour: "2-digit", minute: "2-digit" })].filter(Boolean).join(" · ")}
        </span>
      </span>
      <span className="hidden items-center gap-1.5 sm:flex">
        {m.is_demo && <Badge>{t("matches.demo")}</Badge>}
        <Badge tone={state.tone}>{t(state.label)}</Badge>
      </span>
      {result ? (
        <span className="flex items-center gap-2.5">
          <span className="font-score text-2xl">
            {m.score_own}:{m.score_opponent}
          </span>
          <span
            aria-label={t(`matches.${result}`)}
            className={cn(
              "grid size-6 place-items-center rounded-sm text-xs font-bold ring-1 ring-inset",
              result === "won" ? "bg-ok/10 text-ok ring-ok/40" : result === "lost" ? "bg-error/10 text-error ring-error/40" : "bg-surface text-muted ring-foreground/20",
            )}
          >
            <span aria-hidden>{t(`matches.${result}Short`)}</span>
          </span>
        </span>
      ) : (
        <ChevronRight aria-hidden className="size-4 text-muted transition-transform group-hover:translate-x-0.5" />
      )}
    </Link>
  );
}

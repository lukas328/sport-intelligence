"use client";

import type { Schemas } from "@handball/api-client";
import { Camera, ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { useState } from "react";
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
      {played.length > 0 && <MatchList title={t("matches.played")} orgId={orgId} matches={played} countMissing={canWrite} />}
    </div>
  );
}

function MatchList({ title, orgId, matches, countMissing = false }: { title: string; orgId: string; matches: Match[]; countMissing?: boolean }) {
  const t = useTranslations();
  // demo data said once, not on every row
  const allDemo = matches.every((m) => m.is_demo);
  // what is still open: played matches without a video; the newest of them carries the signal
  const missing = matches.filter((m) => m.score_own != null && matchState(m).label === "matches.noVideoYet");
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="text-2xl">{title}</h2>
        {countMissing && missing.length > 0 && <p className="text-sm text-muted">{t("matches.withoutVideo", { n: missing.length, total: matches.length })}</p>}
        {allDemo && <p className="text-sm text-muted">{t("matches.allDemo")}</p>}
      </div>
      {/* a fixture list on the hall's notice board: rules, no card */}
      <ul className="border-t-2 border-foreground" data-testid="match-list">
        {matches.map((m, i) => (
          <li key={m.id} className={cn(i > 0 && "border-t border-foreground/10")}>
            <MatchRow orgId={orgId} m={m} demoTag={!allDemo} signal={countMissing && m.id === missing[0]?.id} />
          </li>
        ))}
      </ul>
    </section>
  );
}

/** One line of the fixture list: when, where, against whom, how it ended. */
export function MatchRow({ orgId, m, demoTag = true, signal = false }: { orgId: string; m: Match; demoTag?: boolean; signal?: boolean }) {
  const t = useTranslations();
  const format = useFormatter();
  const date = new Date(m.kickoff_at);
  const state = matchState(m);
  const result = m.score_own == null || m.score_opponent == null ? null : m.score_own > m.score_opponent ? "won" : m.score_own < m.score_opponent ? "lost" : "draw";
  // the status only when it asks for something: running, failed, or a played match without video
  const exception = ["matches.status_processing", "matches.status_uploading", "matches.status_failed"].includes(state.label) || (state.label === "matches.noVideoYet" && m.score_own != null);
  const quiet = [m.is_demo && demoTag ? t("matches.demo") : null].filter(Boolean).join(" · ");
  return (
    <Link href={`/app/${orgId}/matches/${m.id}`} className="group grid grid-cols-[3.5rem_minmax(0,1fr)_auto] items-center gap-x-4 px-4 py-4 transition-colors hover:bg-surface sm:grid-cols-[5rem_minmax(0,1fr)_auto] sm:px-5">
      <span className="leading-none">
        <span className="block font-display text-sm text-muted">
          {format.dateTime(date, { weekday: "short" })}
        </span>
        <span className="mt-1 block font-score text-[1.6rem]">{format.dateTime(date, { day: "2-digit", month: "2-digit" })}</span>
      </span>
      <span className="min-w-0">
        <span className="block truncate text-[1.125rem] font-semibold group-hover:text-accent">{m.kind === "training" ? t("matches.training") : m.opponent_name}</span>
        <span className="mt-0.5 block text-sm text-muted">
          {[m.kind !== "training" ? (m.is_home ? t("matches.homeShort") : t("matches.awayShort")) : null, m.competition, format.dateTime(date, { hour: "2-digit", minute: "2-digit" }), quiet || null]
            .filter(Boolean)
            .join(" · ")}
          {exception && (
            <>
              {" · "}
              <span className={cn("text-foreground", signal && "underline decoration-resin decoration-[5px] underline-offset-[5px]")}>{t(state.label)}</span>
            </>
          )}
        </span>
      </span>
      {result ? (
        // the result like the season's form guide: a square with the letter, then the score in ink,
        // the own goals first and the winner's figure bold
        <span className="flex items-center gap-3 whitespace-nowrap">
          <span
            aria-hidden
            className={cn(
              "grid size-8 place-items-center rounded-[4px] font-score text-lg text-background",
              result === "won" ? "bg-ok" : result === "lost" ? "bg-error" : "bg-muted",
            )}
          >
            {t(`matches.${result}`).charAt(0)}
          </span>
          <span className="w-[4.5rem] text-right font-score text-[1.75rem] leading-none tabular-nums sm:w-[5.25rem] sm:text-[2rem]">
            <span className={result === "lost" ? "text-muted" : ""}>{m.score_own}</span>
            <span className="px-0.5 text-muted">:</span>
            <span className={result === "won" ? "text-muted" : ""}>{m.score_opponent}</span>
          </span>
          <span className="sr-only"> {t(`matches.${result}`)}</span>
        </span>
      ) : (
        <ChevronRight aria-hidden className="size-4 text-muted transition-transform group-hover:translate-x-0.5" />
      )}
    </Link>
  );
}

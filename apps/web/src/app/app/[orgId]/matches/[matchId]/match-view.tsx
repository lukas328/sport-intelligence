"use client";

import { ShareButton } from "@/components/sharing/share-button";
import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useRosterNames } from "@/components/analysis/tagger";
import { EmptyState } from "@/components/ui/card";
import type { PlayerHandle } from "@/components/video/player";
import { OverviewView, ReportView, ShotsView, useStats } from "./analysis-views";
import { KeepersView, PhysicalView } from "./m5-views";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import { UploadPanel } from "./upload-panel";
import { Workspace } from "./workspace";
import { useOpponentName } from "@/lib/opponent";
import { TeamFeedView } from "./feed-views";
import { HighlightsView, PartsPanel } from "./highlight-views";

type Match = Schemas["MatchOut"];
type Video = Schemas["VideoOut"];
type Job = Schemas["JobOut"];

type View = "video" | "overview" | "report" | "shots" | "keepers" | "physical" | "highlights" | "scenes";
const VIEWS: View[] = ["video", "overview", "report", "shots", "keepers", "physical", "highlights"];

const STAGES = ["download", "probe", "quality", "transcode", "proxy", "thumbnails", "upload"] as const;

export function MatchView({ orgId, initial, teamName, staff }: { orgId: string; initial: Match; teamName: string; staff: boolean }) {
  const t = useTranslations();
  const oppName = useOpponentName();
  const format = useFormatter();
  const locale = useLocale();
  const qc = useQueryClient();
  const key = ["match", initial.id];
  const { data: match = initial } = useQuery({
    queryKey: key,
    initialData: initial,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: initial.id } } }))
        .data ?? initial,
  });
  const [live, setLive] = useState<Record<string, Partial<Job>>>({});

  // live job progress via Server-Sent Events
  useEffect(() => {
    const es = new EventSource(`/v1/orgs/${orgId}/matches/${initial.id}/stream`);
    es.addEventListener("job", (e) => {
      const ev = JSON.parse((e as MessageEvent).data) as Job & { job_id: string };
      setLive((l) => ({ ...l, [ev.job_id]: ev }));
      if (ev.status === "succeeded" || ev.status === "failed") void qc.invalidateQueries({ queryKey: key });
    });
    return () => es.close();
  }, [orgId, initial.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const [view, setView] = useState<View>("video");
  const player = useRef<PlayerHandle | null>(null);
  // deep links (?t=ms), e.g. from a play drawn on a video moment
  useEffect(() => {
    const t0 = Number(new URLSearchParams(window.location.search).get("t"));
    if (!Number.isFinite(t0) || t0 <= 0) return;
    const id = window.setInterval(() => {
      const v = player.current?.video();
      if (v && v.readyState >= 1) {
        player.current?.seek(t0);
        window.clearInterval(id);
      }
    }, 300);
    const stop = window.setTimeout(() => window.clearInterval(id), 30_000);
    return () => (window.clearInterval(id), window.clearTimeout(stop));
  }, []);
  const stats = useStats(orgId, initial.id);
  const roster = useRosterNames(orgId, match.team_id, match.season_id);
  const names = useMemo(
    () => Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, `${r.jersey_number != null ? `#${r.jersey_number} ` : ""}${r.first_name} ${r.last_name}`])),
    [roster.data],
  );

  const jobs = match.jobs.map((j) => ({ ...j, ...live[j.id] }) as Job);
  const main = match.videos.find((v) => v.role === "main" && v.status === "ready");
  const pendingVideos = match.videos.filter((v) => v.status !== "ready");
  const ourName = teamName;
  const [home, away] = match.is_home ? [ourName, oppName(match)] : [oppName(match), ourName];
  const [hs, as] = match.is_home ? [match.score_own, match.score_opponent] : [match.score_opponent, match.score_own];

  function onPlay(ms: number) {
    setView("video");
    // the player is kept mounted, so the seek works right after the tab switch
    requestAnimationFrame(() => {
      player.current?.seek(ms);
      player.current?.play();
    });
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted">
            {format.dateTime(new Date(match.kickoff_at), { dateStyle: "full", timeStyle: "short" })}
            {match.competition && ` · ${match.competition}`}
            {match.venue && ` · ${match.venue}`}
          </p>
          <h1 className="text-2xl font-semibold">
            {match.opponent ? (
              <>
                {home} <span className="text-muted">{t("matches.vs")}</span> {away}
              </>
            ) : (
              `${t("matches.training")}: ${ourName}`
            )}
          </h1>
          {match.opponent && (
            <a href={`/app/${orgId}/opponents/${match.opponent.id}`} className="text-sm text-accent underline underline-offset-4">
              {t("opponent.open")}: {match.opponent.name}
            </a>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {hs != null && as != null && (
            <p className="text-3xl font-bold tabular-nums" data-testid="score">
              {hs}:{as}
            </p>
          )}
          {match.is_demo && (
            <span className="rounded-full border border-accent px-3 py-1 text-sm font-medium" data-testid="demo-badge">
              {t("matches.demo")}
            </span>
          )}
          <span className="rounded-full bg-surface px-3 py-1 text-sm">{t(`matches.status_${match.status}`)}</span>
          <a
            href={`/v1/orgs/${orgId}/matches/${match.id}/report.pdf?lang=${locale}`}
            className="whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm hover:bg-surface"
            data-testid="pdf"
          >
            {t("matches.pdf")}
          </a>
          {staff && (
            <a href={`/app/${orgId}/matches/${match.id}/live`} className="whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm hover:bg-surface" data-testid="live-link">
              {t("live.open")}
            </a>
          )}
          {staff && match.opponent && (
            <a href={`/app/${orgId}/matches/${match.id}/scouting`} className="whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm hover:bg-surface" data-testid="scouting-link">
              {t("scouting.open")}
            </a>
          )}
          {staff && <ShareButton orgId={orgId} teamId={match.team_id} kind="match" targetId={match.id} />}
        </div>
      </header>

      <nav role="tablist" aria-label={t("tabs.video")} className="flex gap-1 overflow-x-auto border-b border-border">
        {[...VIEWS, ...(staff ? (["scenes"] as View[]) : [])].map((v) => (
          <button
            key={v}
            role="tab"
            aria-selected={view === v}
            onClick={() => setView(v)}
            className={cn("-mb-px border-b-2 px-4 py-2 text-sm font-medium", view === v ? "border-accent" : "border-transparent text-muted hover:text-foreground")}
          >
            {t(`tabs.${v}`)}
          </button>
        ))}
      </nav>

      <div hidden={view !== "video"}>
        {main ? (
          <Workspace orgId={orgId} match={match} video={main} staff={staff} teamName={teamName} handle={player} />
        ) : (
          <Alert kind="info">{match.source === "paper_report" ? t("stats.noVideo") : t("player.notReady")}</Alert>
        )}
      </div>
      {view === "physical" && <PhysicalView orgId={orgId} matchId={match.id} names={names} />}
      {view === "highlights" && <HighlightsView orgId={orgId} matchId={match.id} teamId={match.team_id} staff={staff} names={names} />}
      {view === "scenes" && <TeamFeedView orgId={orgId} matchId={match.id} onPlay={main ? onPlay : undefined} />}
      {view !== "video" &&
        view !== "physical" &&
        view !== "scenes" &&
        view !== "highlights" &&
        (stats.data && stats.data.quality.events > 0 ? (
          (() => {
            const props = { orgId, match, teamName, stats: stats.data, names, staff, onPlay: main ? onPlay : undefined };
            if (view === "overview") return <OverviewView {...props} />;
            if (view === "report") return <ReportView {...props} />;
            if (view === "keepers") return <KeepersView {...props} />;
            return <ShotsView {...props} />;
          })()
        ) : (
          <EmptyState title={stats.isLoading ? "…" : t("stats.noData")} />
        ))}

      <PartsPanel orgId={orgId} matchId={match.id} staff={staff} />
      {jobs.filter((j) => j.status !== "succeeded").length > 0 && <Processing jobs={jobs} orgId={orgId} staff={staff} />}

      {staff && (pendingVideos.length > 0 || !main) && (
        <UploadPanel orgId={orgId} matchId={match.id} onUploaded={() => void qc.invalidateQueries({ queryKey: key })} />
      )}

      {match.videos.map((v) => v.quality_report && <QualityReport key={v.id} video={v} />)}

      {staff && <MatchAdmin orgId={orgId} match={match} teamName={teamName} />}
    </div>
  );
}

function Processing({ jobs, orgId, staff }: { jobs: Job[]; orgId: string; staff: boolean }) {
  const t = useTranslations("processing");
  return (
    <Card className="space-y-4" aria-live="polite">
      <h2 className="text-lg font-semibold">{t("title")}</h2>
      {jobs
        .filter((j) => j.status !== "succeeded")
        .map((j) => (
          <div key={j.id} className="space-y-2" data-testid="job">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{t(j.status as "running")}</span>
              <span className="tabular-nums">{Math.round(j.progress * 100)} %</span>
            </div>
            <div className="h-2 overflow-hidden rounded bg-surface">
              <div className={cn("h-full transition-all", j.status === "failed" ? "bg-error" : "bg-accent")} style={{ width: `${j.progress * 100}%` }} />
            </div>
            {j.kind === "ingest" && (
              <ol className="grid grid-cols-2 gap-1 text-xs sm:grid-cols-4 lg:grid-cols-7">
                {STAGES.map((s) => {
                  const st = (j.stages as Record<string, { status?: string }>)[s]?.status ?? "pending";
                  return (
                    <li key={s} className={cn("rounded px-2 py-1", st === "done" ? "bg-ok/10 text-ok" : st === "running" ? "bg-accent/10 font-medium" : st === "failed" ? "bg-error/10 text-error" : "bg-surface text-muted")}>
                      {t(`stage_${s}`)}
                    </li>
                  );
                })}
              </ol>
            )}
            {j.error && <Alert>{j.error}</Alert>}
            {j.status === "failed" && staff && j.video_asset_id && (
              <Button
                variant="secondary"
                onClick={() =>
                  api.POST("/v1/orgs/{org_id}/videos/{video_id}/reprocess", {
                    params: { path: { org_id: orgId, video_id: j.video_asset_id! } },
                  })
                }
              >
                {t("retry")}
              </Button>
            )}
          </div>
        ))}
    </Card>
  );
}

function QualityReport({ video }: { video: Video }) {
  const t = useTranslations("quality");
  const report = video.quality_report as {
    overall: "ok" | "warn" | "fail";
    checks: { id: string; level: string; value: number | null; tip: string | null }[];
  };
  const color = { ok: "text-ok", warn: "text-accent", fail: "text-error" }[report.overall];
  return (
    <Card className="space-y-3">
      <details>
        <summary className="cursor-pointer">
          <span className="font-semibold">{t("title")}: </span>
          <span className={color}>{t(`overall_${report.overall}`)}</span>
          <span className="ml-2 text-xs text-muted">({t("heuristic")})</span>
        </summary>
        <ul className="mt-3 space-y-2 text-sm">
          {report.checks.map((c) => (
            <li key={c.id} className="flex flex-wrap gap-2">
              <span className="w-40 font-medium">{t(`check_${c.id}` as "check_fps")}</span>
              <span className={c.level === "ok" ? "text-ok" : c.level === "fail" ? "text-error" : c.level === "warn" ? "text-accent" : "text-muted"}>
                {c.level === "not_evaluated" ? t("not_evaluated") : c.tip ? t(`tip_${c.tip}` as "tip_blurry") : "OK"}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </Card>
  );
}

function MatchAdmin({ orgId, match, teamName }: { orgId: string; match: Match; teamName: string }) {
  const t = useTranslations();
  const oppName = useOpponentName();
  const router = useRouter();
  const qc = useQueryClient();
  async function saveScore(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const n = (k: string) => (String(f.get(k) ?? "") === "" ? null : Number(f.get(k)));
    await api.PATCH("/v1/orgs/{org_id}/matches/{match_id}", {
      params: { path: { org_id: orgId, match_id: match.id } },
      body: { score_own: n("score_own"), score_opponent: n("score_opponent"), halftime_own: n("ht_own"), halftime_opponent: n("ht_opp") },
    });
    void qc.invalidateQueries({ queryKey: ["match", match.id] });
  }
  return (
    <Card className="space-y-4">
      <form onSubmit={saveScore} className="flex flex-wrap items-end gap-3" aria-label={t("matches.score")}>
        <fieldset className="flex items-end gap-2">
          <legend className="mb-1 text-sm font-medium">{t("matches.score")}</legend>
          <Input label={teamName} name="score_own" type="number" min={0} max={99} defaultValue={match.score_own ?? ""} className="w-20" />
          <Input label={oppName(match)} name="score_opponent" type="number" min={0} max={99} defaultValue={match.score_opponent ?? ""} className="w-20" />
        </fieldset>
        <fieldset className="flex items-end gap-2">
          <legend className="mb-1 text-sm font-medium">{t("matches.halftime")}</legend>
          <Input label={teamName} name="ht_own" type="number" min={0} max={99} defaultValue={match.halftime_own ?? ""} className="w-20" />
          <Input label={oppName(match)} name="ht_opp" type="number" min={0} max={99} defaultValue={match.halftime_opponent ?? ""} className="w-20" />
        </fieldset>
        <Button type="submit" variant="secondary">
          {t("matches.saveScore")}
        </Button>
      </form>
      <form
        className="flex flex-wrap items-end gap-3"
        aria-label={t("matchForm.format")}
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const format = String(f.get("format"));
          const minutes = Number(f.get("minutes"));
          await api.PATCH("/v1/orgs/{org_id}/matches/{match_id}", {
            params: { path: { org_id: orgId, match_id: match.id } },
            body: format === "custom" ? { format: "custom", period_s: minutes * 60, periods: Number(f.get("periods")) } : { format: format as "mini" },
          });
          void qc.invalidateQueries({ queryKey: ["match", match.id] });
        }}
      >
        <Select label={t("matchForm.format")} name="format" defaultValue={match.format}>
          {["adult_2x30", "youth_2x25", "youth_2x20", "mini", "tournament", "custom"].map((k) => (
            <option key={k} value={k}>
              {t(`matchForm.format_${k}` as "matchForm.format_mini")}
            </option>
          ))}
        </Select>
        <Input label={t("matchForm.minutes")} name="minutes" type="number" min={1} max={60} defaultValue={match.period_s / 60} className="w-24" />
        <Input label={t("matchForm.periods")} name="periods" type="number" min={1} max={4} defaultValue={match.periods} className="w-20" />
        <Button type="submit" variant="secondary">
          {t("matchForm.saveFormat")}
        </Button>
      </form>
      <Button
        variant="danger"
        onClick={async () => {
          if (!window.confirm(t("matches.deleteConfirm"))) return;
          await api.DELETE("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: match.id } } });
          router.push(`/app/${orgId}/teams/${match.team_id}/matches`);
          router.refresh();
        }}
      >
        {t("matches.deleteMatch")}
      </Button>
    </Card>
  );
}

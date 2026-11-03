"use client";

import { ShareButton } from "@/components/sharing/share-button";
import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeftRight, ChevronDown, Binoculars, ChartNoAxesColumn, Clapperboard, FileDown, Hand, MoreHorizontal, Pencil, Radio, Shield, Trash2, Upload } from "lucide-react";
import { useRosterNames } from "@/components/analysis/tagger";
import { Scoreboard } from "@/components/domain/scoreboard";
import { useOptionalShell } from "@/components/shell/context";
import { Badge } from "@/components/ui/badge";
import { EmptyState, Skeleton } from "@/components/ui/card";
import { useConfirm } from "@/components/ui/confirm";
import { Dialog } from "@/components/ui/dialog";
import { MenuContent, MenuItem, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { Segmented } from "@/components/ui/tabs";
import type { PlayerHandle } from "@/components/video/player";
import { OverviewView, ReportView, ShotsView, useStats } from "./analysis-views";
import { KeepersView, PhysicalView } from "./m5-views";
import { Button, buttonClass } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import { UploadPanel } from "./upload-panel";
import { Workspace } from "./workspace";
import { useOpponentName } from "@/lib/opponent";
import { TeamFeedView } from "./feed-views";
import { ExchangePanel } from "./exchange-panel";
import { MarksPanel } from "./marks-panel";
import { HighlightsView, PartsPanel } from "./highlight-views";

type Match = Schemas["MatchOut"];
type Video = Schemas["VideoOut"];
type Job = Schemas["JobOut"];

type View = "video" | "analysis" | "scenes";
type Sub = "overview" | "shots" | "keepers" | "physical" | "report";
const SUBS: Sub[] = ["overview", "shots", "keepers", "physical", "report"];

const STAGES = ["download", "probe", "quality", "transcode", "proxy", "thumbnails", "upload"] as const;

export function MatchView({ orgId, initial, teamName, staff }: { orgId: string; initial: Match; teamName: string; staff: boolean }) {
  const t = useTranslations();
  const oppName = useOpponentName();
  const format = useFormatter();
  const locale = useLocale();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const router = useRouter();
  const shell = useOptionalShell();
  const key = ["match", initial.id];
  const { data: match = initial } = useQuery({
    queryKey: key,
    initialData: initial,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: initial.id } } }))
        .data ?? initial,
  });
  const [live, setLive] = useState<Record<string, Partial<Job>>>({});
  const [dialog, setDialog] = useState<"edit" | "exchange" | null>(null);

  // the shell follows the team of the match (navigation, palette)
  useEffect(() => {
    if (shell && shell.team?.id !== initial.team_id && shell.teams.some((x) => x.id === initial.team_id)) shell.setTeam(initial.team_id);
  }, [initial.team_id]); // eslint-disable-line react-hooks/exhaustive-deps

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
  const [sub, setSub] = useState<Sub>("overview");
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
  const [hh, ah] = match.is_home ? [match.halftime_own, match.halftime_opponent] : [match.halftime_opponent, match.halftime_own];
  const kickoff = new Date(match.kickoff_at);
  const soon = kickoff.getTime() > Date.now() - 3 * 3600_000;
  const liveFirst = staff && match.score_own == null && !main && soon && match.source !== "paper_report";
  const uploadFirst = staff && !main && !liveFirst && match.source !== "paper_report";
  const running = jobs.filter((j) => j.status !== "succeeded");

  function onPlay(ms: number) {
    setView("video");
    // the player is kept mounted, so the seek works right after the switch
    requestAnimationFrame(() => {
      player.current?.seek(ms);
      player.current?.play();
    });
  }

  const base = `/app/${orgId}/matches/${match.id}`;
  return (
    <div className="space-y-8">
      <header className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="eyebrow">
            {[format.dateTime(kickoff, { weekday: "short", day: "numeric", month: "long", year: "numeric" }), format.dateTime(kickoff, { timeStyle: "short" }), match.competition, match.venue]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <div className="flex items-center gap-2">
            {match.is_demo && (
              <Badge tone="accent" data-testid="demo-badge">
                {t("matches.demo")}
              </Badge>
            )}
            {["uploading", "processing", "failed"].includes(match.status) && <Badge tone={match.status === "failed" ? "error" : "accent"}>{t(`matches.status_${match.status}`)}</Badge>}
          </div>
        </div>
        <h1 className="sr-only">
          {match.opponent ? `${home} ${t("matches.vs")} ${away}` : `${t("matches.training")}: ${ourName}`}
        </h1>
        {match.opponent ? (
          <Scoreboard
            home={home}
            away={away}
            homeScore={hs}
            awayScore={as}
            halftime={hh != null && ah != null ? `${hh}:${ah}` : null}
            ownSide={match.is_home ? "home" : "away"}
            vsLabel={t("matches.vs")}
          />
        ) : (
          <p className="text-2xl font-bold font-wide" aria-hidden>
            {t("matches.training")}: {ourName}
          </p>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Segmented<View>
            label={t("tabs.video")}
            value={view}
            onChange={setView}
            items={[
              { value: "video", label: t("tabs.video") },
              { value: "analysis", label: t("tabs.analysis") },
              { value: "scenes", label: t("tabs.scenes") },
            ]}
          />
          <div className="flex items-center gap-2">
            {liveFirst && (
              <Link href={`${base}/live`} className={buttonClass("primary")} data-testid="live-link">
                <Radio aria-hidden />
                {t("live.open")}
              </Link>
            )}
            {uploadFirst && (
              <Button onClick={() => (setView("video"), document.getElementById("upload")?.scrollIntoView({ behavior: "smooth" }))}>
                <Upload aria-hidden />
                {t("upload.title")}
              </Button>
            )}
            {staff && <ShareButton orgId={orgId} teamId={match.team_id} kind="match" targetId={match.id} />}
            <MenuRoot>
              <MenuTrigger className={buttonClass("secondary", "icon")} aria-label={t("common.more")} data-testid="match-menu">
                <MoreHorizontal aria-hidden />
              </MenuTrigger>
              <MenuContent>
                <MenuItem href={`/v1/orgs/${orgId}/matches/${match.id}/report.pdf?lang=${locale}`} external icon={<FileDown />} testId="pdf">
                  {t("matches.pdf")}
                </MenuItem>
                {staff && !liveFirst && (
                  <MenuItem href={`${base}/live`} icon={<Radio />} testId="live-link">
                    {t("live.open")}
                  </MenuItem>
                )}
                {staff && (
                  <MenuItem href={`${base}/marks`} icon={<Hand />} testId="marks-link">
                    {t("marks.title")}
                  </MenuItem>
                )}
                {staff && match.opponent && (
                  <MenuItem href={`${base}/scouting`} icon={<Binoculars />} testId="scouting-link">
                    {t("scouting.open")}
                  </MenuItem>
                )}
                {match.opponent && (
                  <MenuItem href={`/app/${orgId}/opponents/${match.opponent.id}`} icon={<Shield />}>
                    {t("opponent.open")}: {match.opponent.name}
                  </MenuItem>
                )}
                <MenuSeparator />
                <MenuItem onSelect={() => setDialog("exchange")} icon={<ArrowLeftRight />}>
                  {t("exchange.title")}
                </MenuItem>
                {staff && (
                  <MenuItem onSelect={() => setDialog("edit")} icon={<Pencil />}>
                    {t("matches.edit")}
                  </MenuItem>
                )}
                {staff && (
                  <MenuItem
                    danger
                    icon={<Trash2 />}
                    onSelect={async () => {
                      if (!(await confirm({ title: t("matches.deleteMatch"), body: t("matches.deleteConfirm"), confirm: t("common.delete"), danger: true }))) return;
                      await api.DELETE("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: match.id } } });
                      router.push(`/app/${orgId}/teams/${match.team_id}/matches`);
                      router.refresh();
                    }}
                  >
                    {t("matches.deleteMatch")}
                  </MenuItem>
                )}
              </MenuContent>
            </MenuRoot>
          </div>
        </div>
      </header>

      {running.length > 0 && <Processing jobs={jobs} orgId={orgId} staff={staff} />}

      <div hidden={view !== "video"} className="space-y-6">
        {main ? (
          <Workspace orgId={orgId} match={match} video={main} staff={staff} teamName={teamName} handle={player} />
        ) : !(staff && match.source !== "paper_report") ? (
          <EmptyState icon={<Clapperboard />} title={match.source === "paper_report" ? t("stats.noVideo") : t("player.notReady")} />
        ) : null}
        {staff && (pendingVideos.length > 0 || !main) && match.source !== "paper_report" && (
          <div id="upload" className="scroll-mt-24">
            <UploadPanel orgId={orgId} matchId={match.id} onUploaded={() => void qc.invalidateQueries({ queryKey: key })} />
          </div>
        )}
        <PartsPanel orgId={orgId} matchId={match.id} staff={staff} />
        {match.videos.map((v) => v.quality_report && <QualityReport key={v.id} video={v} />)}
      </div>

      {view === "analysis" && (
        <div className="animate-fade space-y-6">
          <Segmented<Sub>
            label={t("tabs.analysis")}
            size="sm"
            value={sub}
            onChange={setSub}
            items={SUBS.map((v) => ({ value: v, label: t(`tabs.${v}`) }))}
          />
          <div key={sub} className="animate-fade">
          {sub === "physical" ? (
            <PhysicalView orgId={orgId} matchId={match.id} names={names} />
          ) : stats.data && stats.data.quality.events > 0 ? (
            (() => {
              const props = { orgId, match, teamName, stats: stats.data, names, staff, onPlay: main ? onPlay : undefined };
              if (sub === "overview") return <OverviewView {...props} />;
              if (sub === "report") return <ReportView {...props} />;
              if (sub === "keepers") return <KeepersView {...props} />;
              return <ShotsView {...props} />;
            })()
          ) : stats.isLoading ? (
            <Skeleton className="h-64" />
          ) : (
            <EmptyState icon={<ChartNoAxesColumn />} title={t("stats.noData")}>
              {staff && !main && match.source !== "paper_report" ? t("stats.noDataHint") : null}
            </EmptyState>
          )}
          </div>
        </div>
      )}

      {view === "scenes" && (
        <div className="animate-fade space-y-8">
          <HighlightsView orgId={orgId} matchId={match.id} teamId={match.team_id} staff={staff} names={names} />
          {staff && <MarksPanel orgId={orgId} matchId={match.id} onPlay={main ? onPlay : undefined} />}
          {staff && <TeamFeedView orgId={orgId} matchId={match.id} onPlay={main ? onPlay : undefined} />}
        </div>
      )}

      <Dialog open={dialog === "edit"} onOpenChange={(o) => setDialog(o ? "edit" : null)} title={t("matches.edit")}>
        <MatchAdmin orgId={orgId} match={match} teamName={teamName} onSaved={() => setDialog(null)} />
      </Dialog>
      <Dialog open={dialog === "exchange"} onOpenChange={(o) => setDialog(o ? "exchange" : null)} title={t("exchange.title")}>
        <ExchangePanel orgId={orgId} matchId={match.id} canImport={staff} />
      </Dialog>
    </div>
  );
}

function Processing({ jobs, orgId, staff }: { jobs: Job[]; orgId: string; staff: boolean }) {
  const t = useTranslations("processing");
  return (
    <Card className="space-y-5" aria-live="polite">
      <h2 className="text-base font-semibold">{t("title")}</h2>
      {jobs
        .filter((j) => j.status !== "succeeded")
        .map((j) => (
          <div key={j.id} className="space-y-3" data-testid="job">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{t(j.status as "running")}</span>
              <span className="font-semibold tabular-nums">{Math.round(j.progress * 100)} %</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-surface">
              <div className={cn("h-full rounded-full transition-all duration-500", j.status === "failed" ? "bg-error" : "bg-accent")} style={{ width: `${j.progress * 100}%` }} />
            </div>
            {j.kind === "ingest" && (
              <ol className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
                {STAGES.map((s) => {
                  const st = (j.stages as Record<string, { status?: string }>)[s]?.status ?? "pending";
                  return (
                    <li key={s} className={cn("flex items-center gap-1.5", st === "done" ? "text-ok" : st === "running" ? "font-semibold text-foreground" : st === "failed" ? "text-error" : "text-muted")}>
                      <span aria-hidden className={cn("size-1.5 rounded-full", st === "done" ? "bg-ok" : st === "running" ? "animate-pulse bg-accent" : st === "failed" ? "bg-error" : "bg-border")} />
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
                size="sm"
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
  const tone = { ok: "text-ok", warn: "text-warn", fail: "text-error" }[report.overall];
  return (
    <details className="group rounded-2xl bg-raised px-5 py-4 ring-1 ring-border/70">
      <summary className="flex cursor-pointer list-none items-center gap-2 text-sm [&::-webkit-details-marker]:hidden">
        <span className="font-medium">{t("title")}:</span>
        <span className={cn("font-medium", tone)}>{t(`overall_${report.overall}`)}</span>
        <span className="text-xs text-muted">({t("heuristic")})</span>
        <ChevronDown aria-hidden className="ml-auto size-4 text-muted transition-transform group-open:rotate-180" />
      </summary>
      <ul className="mt-4 divide-y divide-border/70 text-sm">
        {report.checks.map((c) => (
          <li key={c.id} className="flex flex-wrap gap-x-4 gap-y-1 py-2">
            <span className="w-44 shrink-0 text-muted">{t(`check_${c.id}` as "check_fps")}</span>
            <span className={c.level === "ok" ? "text-ok" : c.level === "fail" ? "text-error" : c.level === "warn" ? "text-warn" : "text-muted"}>
              {c.level === "not_evaluated" ? t("not_evaluated") : c.tip ? t(`tip_${c.tip}` as "tip_blurry") : "OK"}
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}

function MatchAdmin({ orgId, match, teamName, onSaved }: { orgId: string; match: Match; teamName: string; onSaved: () => void }) {
  const t = useTranslations();
  const oppName = useOpponentName();
  const qc = useQueryClient();
  const [custom, setCustom] = useState(match.format === "custom");
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const n = (k: string) => (String(f.get(k) ?? "") === "" ? null : Number(f.get(k)));
    const format = String(f.get("format"));
    await api.PATCH("/v1/orgs/{org_id}/matches/{match_id}", {
      params: { path: { org_id: orgId, match_id: match.id } },
      body: {
        score_own: n("score_own"),
        score_opponent: n("score_opponent"),
        halftime_own: n("ht_own"),
        halftime_opponent: n("ht_opp"),
        ...(format === "custom" ? { format: "custom" as const, period_s: Number(f.get("minutes")) * 60, periods: Number(f.get("periods")) } : { format: format as "mini" }),
      },
    });
    await qc.invalidateQueries({ queryKey: ["match", match.id] });
    onSaved();
  }
  return (
    <form onSubmit={save} className="space-y-6" aria-label={t("matches.edit")}>
      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="mb-2 text-sm font-semibold">{t("matches.score")}</legend>
        <Input label={teamName} name="score_own" type="number" min={0} max={99} defaultValue={match.score_own ?? ""} />
        <Input label={oppName(match)} name="score_opponent" type="number" min={0} max={99} defaultValue={match.score_opponent ?? ""} />
      </fieldset>
      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="mb-2 text-sm font-semibold">{t("matches.halftime")}</legend>
        <Input label={teamName} name="ht_own" type="number" min={0} max={99} defaultValue={match.halftime_own ?? ""} />
        <Input label={oppName(match)} name="ht_opp" type="number" min={0} max={99} defaultValue={match.halftime_opponent ?? ""} />
      </fieldset>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <Select label={t("matchForm.format")} name="format" defaultValue={match.format} onChange={(e) => setCustom(e.target.value === "custom")}>
            {["adult_2x30", "youth_2x25", "youth_2x20", "mini", "tournament", "custom"].map((k) => (
              <option key={k} value={k}>
                {t(`matchForm.format_${k}` as "matchForm.format_mini")}
              </option>
            ))}
          </Select>
        </div>
        {custom && (
          <>
            <Input label={t("matchForm.minutes")} name="minutes" type="number" min={1} max={60} defaultValue={match.period_s / 60} />
            <Input label={t("matchForm.periods")} name="periods" type="number" min={1} max={4} defaultValue={match.periods} />
          </>
        )}
      </div>
      <Button type="submit">{t("common.save")}</Button>
    </form>
  );
}

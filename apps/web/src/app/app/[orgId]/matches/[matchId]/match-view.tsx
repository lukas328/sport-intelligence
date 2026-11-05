"use client";

import { ShareButton } from "@/components/sharing/share-button";
import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useFormatter, useLocale, useNow, useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeftRight, Check, ChevronDown, ImageDown, Binoculars, ChartNoAxesColumn, Clapperboard, FileDown, Hand, MoreHorizontal, Pencil, Plus, Radio, Shield, Trash2, Upload } from "lucide-react";
import { useRosterNames } from "@/components/analysis/tagger";
import { KitFields } from "@/components/domain/kit-fields";
import { useCountUp } from "@/components/domain/match-score";
import { cardFileName, drawMatchCard } from "@/lib/match-card";
import { DEFAULT_CLUB } from "@/lib/color";
import type { Kits } from "@/lib/kit";
import { playerLabel } from "@/lib/player-name";
import { Stage, StageTag } from "@/components/domain/stage";
import { useOptionalShell } from "@/components/shell/context";
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
import { formatClock } from "@/lib/format";
import { coverage } from "@/lib/match-workflow";
import { TeamFeedView } from "./feed-views";
import { ExchangePanel } from "./exchange-panel";
import { officialGoalsKey } from "./official-goals";
import { VideoOverview } from "./video-overview";
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
  const [justDone, setJustDone] = useState(false);

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
      // a new analysis reads the goals again: the comparison with the official report changes
      if (ev.status === "succeeded") {
        void qc.invalidateQueries({ queryKey: officialGoalsKey(initial.id) });
        void qc.invalidateQueries({ queryKey: ["goal-candidates", initial.id] });
        void qc.invalidateQueries({ queryKey: ["analysis"] });
      }
      // the moment the analysis is done: said on the stage, not in a toast
      if (ev.status === "succeeded" && ev.kind !== "ingest") setJustDone(true);
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
    () => Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, playerLabel(r.jersey_number, `${r.first_name} ${r.last_name}`)])),
    [roster.data],
  );

  const jobs = match.jobs.map((j) => ({ ...j, ...live[j.id] }) as Job);
  const main = match.videos.find((v) => v.role === "main" && v.status === "ready");
  // a match with events but no video (paper report, demo, marks) opens on its analysis
  const opened = useRef(false);
  const hasEvents = (stats.data?.own.shots ?? 0) + (stats.data?.opponent.shots ?? 0) > 0;
  useEffect(() => {
    if (opened.current || !stats.data) return;
    opened.current = true;
    if (!main && hasEvents && !new URLSearchParams(window.location.search).get("t")) setView("analysis");
  }, [stats.data, main, hasEvents]);
  const pendingVideos = match.videos.filter((v) => v.status !== "ready");
  const ourName = teamName;
  const [home, away] = match.is_home ? [ourName, oppName(match)] : [oppName(match), ourName];
  const [hs, as] = match.is_home ? [match.score_own, match.score_opponent] : [match.score_opponent, match.score_own];
  const [hh, ah] = match.is_home ? [match.halftime_own, match.halftime_opponent] : [match.halftime_opponent, match.halftime_own];
  const kickoff = new Date(match.kickoff_at);
  const result = match.opponent && match.score_own != null && match.score_opponent != null ? (match.score_own > match.score_opponent ? "won" : match.score_own < match.score_opponent ? "lost" : "draw") : null;
  const soon = kickoff.getTime() > Date.now() - 3 * 3600_000;
  const liveFirst = staff && match.score_own == null && !main && soon && match.source !== "paper_report";
  const uploadFirst = staff && !main && !liveFirst && match.source !== "paper_report";
  const running = jobs.filter((j) => j.status !== "succeeded");

  /** Match card (4:5 PNG), drawn locally: club, team, date, score, opponent, two figures. */
  async function downloadCard() {
    if (match.score_own == null || match.score_opponent == null) return;
    await document.fonts?.ready;
    const pctOf = (v: number | null | undefined) => (v == null ? null : `${Math.round(v * 100)} %`);
    const shots = pctOf(stats.data?.own.shooting_pct);
    const saves = pctOf(stats.data?.own.save_pct);
    const date = format.dateTime(kickoff, { day: "2-digit", month: "2-digit", year: "2-digit" });
    const canvas = drawMatchCard(document.createElement("canvas"), {
      club: shell?.org.name ?? "",
      team: teamName,
      date,
      own: match.score_own,
      opp: match.score_opponent,
      opponent: oppName(match),
      line: t(`voice.${result === "won" ? "won" : result === "lost" ? "lost" : "draw"}`, { opponent: oppName(match) }).replace(/\.$/, ""),
      figures: [shots && t("matches.cardShots", { value: shots }), saves && t("matches.cardSaves", { value: saves })].filter((x): x is string => Boolean(x)),
      colour: shell?.org.primary_color ?? DEFAULT_CLUB,
      tag: match.is_demo ? t("matches.cardDemo") : null,
    });
    const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, "image/png"));
    if (!blob) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = cardFileName(teamName, oppName(match), date);
    a.click();
    window.setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  // numbers in the analysis and scenes views jump to a moment: bring the player into view, the
  // focus stays where it is
  function reveal() {
    const v = player.current?.video();
    if (!v) return;
    const box = v.getBoundingClientRect();
    if (box.top >= 0 && box.bottom <= window.innerHeight) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    v.scrollIntoView({ block: "nearest", behavior: still ? "auto" : "smooth" });
  }

  function onPlay(ms: number) {
    setView("video");
    // the player is kept mounted, so the seek works right after the switch
    requestAnimationFrame(() => {
      player.current?.seek(ms);
      player.current?.play();
      reveal();
    });
  }

  const base = `/app/${orgId}/matches/${match.id}`;
  // what the video covers of the match, for the analysis to say which figures it can carry
  const covers = main ? coverage(match.kickoff_ms, match.period_s, main.duration_s ? main.duration_s * 1000 : null) : null;
  const videoNote = covers?.length
    ? t("workflow.coverage", { clip: covers.map((c) => `${formatClock(c.from * 1000)} ${t("workflow.to")} ${formatClock(c.to * 1000)}`).join(", ") })
    : null;
  // the main video is there: more cameras (goal cameras, a second angle) and the quality of the
  // recording belong to the court step of the workspace, not under every step
  const setup = main ? (
    <>
      {match.videos.map((v) => v.quality_report && <QualityReport key={v.id} video={v} />)}
      {staff && match.source !== "paper_report" && (
        <details id="upload" className="group" open={pendingVideos.length > 0 && pendingVideos.some((v) => v.status === "processing")}>
          <summary className="flex cursor-pointer list-none items-center gap-1.5 text-sm font-medium text-muted hover:text-foreground [&::-webkit-details-marker]:hidden">
            <Plus aria-hidden className="size-4" />
            {t("upload.addCamera")}
          </summary>
          <div className="pt-3">
            <UploadPanel orgId={orgId} matchId={match.id} onUploaded={() => void qc.invalidateQueries({ queryKey: key })} />
          </div>
        </details>
      )}
    </>
  ) : null;
  return (
    <div className="space-y-8">
      <Stage
        compact
        aside={
          stats.data && hasEvents ? (
            // phones, video view: the score is enough; the figures sit in the analysis
            <div className={cn(view === "video" && "max-sm:hidden")}>
            <table className="text-[0.9375rem]">
              <caption className="sr-only">{t("stats.comparison")}</caption>
              <thead>
                <tr className="text-sm">
                  <th scope="col" className="sr-only">
                    {t("stats.comparison")}
                  </th>
                  <th scope="col" className="px-3 pb-1 text-right font-semibold">{t("stats.own")}</th>
                  <th scope="col" className="pb-1 pl-3 text-right font-semibold opacity-80">{t("stats.opponent")}</th>
                </tr>
              </thead>
              <tbody>
                {(stats.data.quality.attempts_known === false
                  ? // only goals are known (score overlay): attacks and goals per attack; the score says the goals
                    [
                      [t("stats.possessions"), stats.data.own.possessions ?? "-", stats.data.opponent.possessions ?? "-"],
                      [t("stats.efficiency"), pctLabel(stats.data.own.attack_efficiency), pctLabel(stats.data.opponent.attack_efficiency)],
                    ]
                  : [
                      [t("stats.shootingPct"), pctLabel(stats.data.own.shooting_pct), pctLabel(stats.data.opponent.shooting_pct)],
                      [t("stats.savePct"), pctLabel(stats.data.own.save_pct), pctLabel(stats.data.opponent.save_pct)],
                      [t("stats.turnovers"), stats.data.own.turnovers, stats.data.opponent.turnovers],
                      [t("stats.xg"), stats.data.own.xg.toFixed(1), stats.data.opponent.xg.toFixed(1)],
                    ]
                )
                  // a row of dashes says nothing on the stage
                  .filter(([, a, b]) => !(a === "-" && b === "-"))
                  .map(([label, a, b]) => (
                  <tr key={String(label)} className="border-t border-current/20">
                    <th scope="row" className="py-1.5 pr-4 text-left font-medium">{label}</th>
                    <td className="px-3 py-1.5 text-right font-score text-2xl leading-none">{a}</td>
                    <td className="py-1.5 pl-3 text-right font-score text-2xl leading-none opacity-80">{b}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          ) : undefined
        }
      >
        <p className="text-[0.9375rem] font-semibold">
          {[format.dateTime(kickoff, { weekday: "short", day: "numeric", month: "long", year: "numeric" }), format.dateTime(kickoff, { timeStyle: "short" }), match.competition, match.venue]
            .filter(Boolean)
            .join(" · ")}
        </p>
        <h1 className="sr-only">{match.opponent ? `${home} ${t("matches.vs")} ${away}` : `${t("matches.training")}: ${ourName}`}</h1>
        {hs != null && as != null && <span className="sr-only" data-testid="score">{`${hs}:${as}`}</span>}
        {match.opponent ? (
          <ScoreRows home={home} away={away} hs={hs} as={as} ownHome={match.is_home} halftime={hh != null && ah != null ? `${hh}:${ah}` : null} halftimeLabel={t("matches.halftime")} />
        ) : (
          <p aria-hidden className="mt-2 text-[2.25rem] leading-[0.95] font-display sm:text-5xl">
            {t("matches.training")}: {ourName}
          </p>
        )}
        {(result || match.is_demo || justDone || ["uploading", "processing", "failed"].includes(match.status)) && (
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-lg">
            {result && <span className="font-semibold">{t(`matches.${result}`)}</span>}
            {match.is_demo && (
              <span data-testid="demo-badge">
                <StageTag>{t("matches.demo")}</StageTag>
              </span>
            )}
            {justDone && (
              <span role="status" className="inline-flex items-center gap-1.5 font-semibold">
                <Check aria-hidden className="size-4" />
                {t("processing.done")}
              </span>
            )}
            {["uploading", "processing", "failed"].includes(match.status) && <StageTag>{t(`matches.status_${match.status}`)}</StageTag>}
          </div>
        )}
      </Stage>
      <div className="space-y-6">
        <div className="flex items-end justify-between gap-3 border-b border-foreground/15">
          <Segmented<View>
            className="min-w-0"
            variant="underline"
            label={t("tabs.video")}
            value={view}
            onChange={setView}
            items={[
              { value: "video", label: t("tabs.video") },
              { value: "analysis", label: t("tabs.analysis") },
              { value: "scenes", label: t("tabs.scenes") },
            ]}
          />
          <div className="flex items-center gap-2 pb-2.5">
            {liveFirst && (
              <Link href={`${base}/live`} className={buttonClass("primary")} data-testid="live-link">
                <Radio aria-hidden />
                {t("live.open")}
              </Link>
            )}
            {uploadFirst && view !== "video" && (
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
                {staff && match.opponent && match.score_own != null && match.score_opponent != null && (
                  <MenuItem icon={<ImageDown />} onSelect={() => void downloadCard()} testId="match-card">
                    {t("matches.card")}
                  </MenuItem>
                )}
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
      </div>

      {running.length > 0 && <Processing jobs={jobs} orgId={orgId} staff={staff} />}

      <div hidden={view !== "video"} className="space-y-6">
        {main ? (
          <Workspace orgId={orgId} match={match} video={main} staff={staff} teamName={teamName} oppName={oppName(match)} names={names} handle={player} setup={setup} />
        ) : !(staff && match.source !== "paper_report") ? (
          <EmptyState icon={<Clapperboard />} title={match.source === "paper_report" ? t("stats.noVideo") : t("player.notReady")} />
        ) : null}
        {staff && match.source !== "paper_report" && !main && (
          <div id="upload" className="scroll-mt-24">
            <UploadPanel orgId={orgId} matchId={match.id} onUploaded={() => void qc.invalidateQueries({ queryKey: key })} />
          </div>
        )}
        <PartsPanel orgId={orgId} matchId={match.id} staff={staff} />
        {!main && match.videos.map((v) => v.quality_report && <QualityReport key={v.id} video={v} />)}
      </div>

      {view === "analysis" && (
        <div className="animate-fade space-y-6">
          <Segmented<Sub>
            label={t("tabs.analysis")}
            variant="underline"
            className="border-b border-foreground/15"
            size="sm"
            value={sub}
            onChange={setSub}
            items={SUBS.map((v) => ({ value: v, label: t(`tabs.${v}`) }))}
          />
          <div key={sub} className="animate-fade">
          {sub === "physical" ? (
            <PhysicalView
              orgId={orgId}
              matchId={match.id}
              names={names}
              teamName={teamName}
              oppName={oppName(match)}
              videoNote={videoNote}
              short={covers != null && covers.reduce((s, c) => s + c.to - c.from, 0) < match.period_s}
            />
          ) : stats.data && stats.data.quality.events > 0 ? (
            (() => {
              const props = { orgId, match, teamName, stats: stats.data, names, staff, onPlay: main ? onPlay : undefined };
              if (sub === "overview")
                return (
                  <div className="space-y-10">
                    <OverviewView {...props} videoNote={videoNote} />
                    {/* what the video itself shows (possession, attacks) belongs to the overview too */}
                    {main && (
                      <VideoOverview
                        orgId={orgId}
                        matchId={match.id}
                        teamId={match.team_id}
                        ownName={teamName}
                        oppName={oppName(match)}
                        durationMs={main.duration_s ? main.duration_s * 1000 : null}
                        kickoff={match.kickoff_ms}
                        periodS={match.period_s}
                        onPlay={onPlay}
                        onPhysical={() => setSub("physical")}
                        staff={false}
                        compact
                      />
                    )}
                  </div>
                );
              if (sub === "report") return <ReportView {...props} />;
              if (sub === "keepers") return <KeepersView {...props} />;
              return <ShotsView {...props} />;
            })()
          ) : stats.isLoading ? (
            <Skeleton className="h-64" />
          ) : main ? (
            <VideoOverview
              orgId={orgId}
              matchId={match.id}
              teamId={match.team_id}
              ownName={teamName}
              oppName={oppName(match)}
              durationMs={main.duration_s ? main.duration_s * 1000 : null}
              kickoff={match.kickoff_ms}
              periodS={match.period_s}
              onPlay={onPlay}
              onPhysical={() => setSub("physical")}
              staff={staff}
            />
          ) : (
            <EmptyState icon={<ChartNoAxesColumn />} title={t("stats.noData")}>
              {staff && match.source !== "paper_report" ? t("stats.noDataHint") : null}
            </EmptyState>
          )}
          </div>
        </div>
      )}

      {view === "scenes" && (
        <div className="animate-fade space-y-8">
          {/* the coach's job here first: feedback per player; then the reels to share */}
          {staff && <TeamFeedView orgId={orgId} matchId={match.id} onPlay={main ? onPlay : undefined} kickoff={match.kickoff_ms} periodS={match.period_s} />}
          <HighlightsView orgId={orgId} matchId={match.id} teamId={match.team_id} staff={staff} names={names} />
          {staff && <MarksPanel orgId={orgId} matchId={match.id} onPlay={main ? onPlay : undefined} />}
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
  const now = useNow({ updateInterval: 5000 });
  return (
    <Card className="space-y-5" aria-live="polite">
      {jobs
        .filter((j) => j.status !== "succeeded")
        .map((j) => {
          // the stages the worker reported, in its order (ingest and analysis have different ones)
          const reported = Object.keys((j.stages ?? {}) as Record<string, unknown>);
          const stages = reported.length > 0 ? reported : j.kind === "ingest" ? [...STAGES] : [];
          const started = j.started_at ? new Date(j.started_at).getTime() : null;
          const elapsed = started ? (now.getTime() - started) / 1000 : 0;
          const etaMin =
            j.status === "running" && j.progress > 0.05 && elapsed > 20
              ? Math.max(1, Math.round(((elapsed / j.progress) * (1 - j.progress)) / 60))
              : null;
          return (
            <div key={j.id} className="space-y-3" data-testid="job">
              <h2 className="text-base font-semibold">{t(j.kind === "analysis" ? "titleAnalysis" : "title")}</h2>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium">
                  {t(j.status as "running")}
                  {etaMin != null && <span className="font-normal text-muted"> · {t("eta", { minutes: etaMin })}</span>}
                </span>
                <span className="font-semibold tabular-nums">{Math.round(j.progress * 100)} %</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-surface">
                <div className={cn("h-full rounded-full transition-all duration-500", j.status === "failed" ? "bg-error" : "bg-accent")} style={{ width: `${j.progress * 100}%` }} />
              </div>
              {stages.length > 0 && (
                <ol className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
                  {stages.map((s) => {
                    const st = (j.stages as Record<string, { status?: string }>)[s]?.status ?? "pending";
                    return (
                      <li key={s} className={cn("flex items-center gap-1.5", st === "done" ? "text-ok" : st === "running" ? "font-semibold text-foreground" : st === "failed" ? "text-error" : "text-muted")}>
                        <span aria-hidden className={cn("size-1.5 rounded-full", st === "done" ? "bg-ok" : st === "running" ? "animate-pulse bg-accent" : st === "failed" ? "bg-error" : "bg-border")} />
                        {t.has(`stage_${j.kind}_${s}`) ? t(`stage_${j.kind}_${s}` as "stage_download") : t.has(`stage_${s}`) ? t(`stage_${s}` as "stage_download") : s}
                      </li>
                    );
                  })}
                </ol>
              )}
              {j.kind === "analysis" && j.status === "running" && <p className="text-sm text-muted">{t("analysisHint")}</p>}
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
          );
        })}
    </Card>
  );
}

function QualityReport({ video }: { video: Video }) {
  const t = useTranslations("quality");
  const report = video.quality_report as {
    overall: "ok" | "warn" | "fail";
    checks: { id: string; level: string; value: number | null; tip: string | null }[];
  };
  // quiet unless the recording fails: the signal colour belongs to the open work step
  const tone = report.overall === "fail" ? "text-error" : "";
  return (
    <details className="group">
      <summary className="flex cursor-pointer list-none items-center gap-2 text-sm [&::-webkit-details-marker]:hidden">
        <span className="font-medium">{t("title")}:</span>
        <span className={cn("font-medium", tone)}>{t(`overall_${report.overall}`)}</span>
        <span className="text-xs text-muted">({t("heuristic")})</span>
        <ChevronDown aria-hidden className="ml-auto size-4 text-muted transition-transform group-open:rotate-180" />
      </summary>
      <ul className="mt-3 divide-y divide-border/70 text-sm">
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
  const saved: Kits = {
    own: match.kit_own,
    own_gk: match.kit_own_gk,
    opponent: match.kit_opponent,
    opponent_gk: match.kit_opponent_gk,
    referee: match.kit_referee ?? null,
  };
  const [kits, setKits] = useState(saved);
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
        // only the kits that changed: null clears the referee kit
        ...Object.fromEntries((Object.keys(kits) as (keyof Kits)[]).filter((k) => kits[k] !== saved[k]).map((k) => [`kit_${k}`, kits[k]])),
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
      <fieldset>
        <legend className="mb-2 text-sm font-semibold">{t("matches.kits")}</legend>
        <KitFields kits={kits} onChange={setKits} />
      </fieldset>
      <Button type="submit">{t("common.save")}</Button>
    </form>
  );
}

/** The two teams as rows of a scoreboard: name left, goals right, our row in full strength. */
// a share above 100 % means the sources disagree (e.g. goals from a report, attacks from a clip)
const pctLabel = (v: number | null | undefined) => (v == null || v > 1 ? "-" : `${Math.round(v * 100)} %`);

function ScoreRows({ home, away, hs, as, ownHome, halftime, halftimeLabel }: { home: string; away: string; hs: number | null; as: number | null; ownHome: boolean; halftime: string | null; halftimeLabel: string }) {
  const [h, a] = useCountUp(hs ?? 0, as ?? 0);
  const scored = hs != null && as != null;
  const row = (name: string, goals: number, own: boolean) => (
    <>
      <span className={cn("min-w-0 truncate text-[2rem] leading-[1.1] font-display sm:text-[2.75rem]", !own && "opacity-75")}>{name}</span>
      {scored ? <span className={cn("text-right font-score text-[2.5rem] leading-[1.05] sm:text-[3.25rem]", !own && "opacity-75")}>{goals}</span> : <span />}
    </>
  );
  return (
    <div aria-hidden className="mt-3">
      <div className="grid max-w-full grid-cols-[minmax(0,auto)_auto] items-baseline gap-x-8 sm:w-fit sm:gap-x-12">
        {row(home, h, ownHome)}
        {row(away, a, !ownHome)}
      </div>
      {halftime && (
        <p className="pt-1 text-sm font-semibold">
          {halftimeLabel} {halftime}
        </p>
      )}
    </div>
  );
}

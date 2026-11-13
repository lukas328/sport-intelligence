"use client";

import { ShareButton } from "@/components/sharing/share-button";
import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useFormatter, useLocale, useNow, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeftRight, Check, ChevronDown, ChartNoAxesColumn, Clapperboard, FileDown, Hand, MoreHorizontal, Pencil, Plus, Radio, Shield, Trash2, Upload } from "lucide-react";
import { useRosterNames } from "@/components/analysis/tagger";
import { KitFields } from "@/components/domain/kit-fields";
import { AttendancePanel } from "@/components/team/attendance-panel";
import { cardFileName, drawMatchCard } from "@/lib/match-card";
import { DEFAULT_CLUB, matchStyle } from "@/lib/color";
import { goalRuns, useMatchGraphics } from "@/lib/graphics";
import { threeThings } from "@/lib/three-things";
import { ownName } from "@/lib/own-name";
import { ThreeThingsView, useThingText } from "@/components/anlauf/three-things-view";
import { EmptyField } from "@/components/anlauf/bundle";
import { MatchHead } from "./match-head";
import { AskColour } from "./ask-colour";
import { MatchZones } from "./match-graphics";
import { VideoStage } from "./video-stage";
import type { Kits } from "@/lib/kit";
import { playerLabel } from "@/lib/player-name";
import { useOptionalShell } from "@/components/shell/context";
import { EmptyState, Skeleton } from "@/components/ui/card";
import { useConfirm } from "@/components/ui/confirm";
import { Dialog } from "@/components/ui/dialog";
import { MenuContent, MenuItem, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { Segmented } from "@/components/ui/tabs";
import type { PlayerHandle } from "@/components/video/player";
import { FromMatchButton } from "@/components/collections/from-match";
import { GameActions, PointOpen, Telegram, ThreeFigures, chatPicture } from "./game-tab";
import { ConcededByPosition, OverviewView, ReportView, ShotsView, useStats } from "./analysis-views";
import { KeepersView, PhysicalView } from "./m5-views";
import { NumbersView } from "./numbers-view";
import { Button, buttonClass } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import { UploadPanel } from "./upload-panel";
import { Workspace } from "./workspace";
import { useOpponentName } from "@/lib/opponent";
import { formatClock } from "@/lib/format";
import { coverage } from "@/lib/match-workflow";
import { FeedbackSummary, MyScenesLine, TeamFeedView } from "./feed-views";
import { ExchangePanel } from "./exchange-panel";
import { officialGoalsKey } from "./official-goals";
import { VideoOverview } from "./video-overview";
import { MarksPanel } from "./marks-panel";
import { HighlightsView, PartsPanel } from "./highlight-views";

type Match = Schemas["MatchOut"];
type Video = Schemas["VideoOut"];
type Job = Schemas["JobOut"];

/** One level of tabs (SPEC 7.2 to 7.4): Spiel, Video, Zahlen. */
type View = "game" | "video" | "numbers";
const VIEW_PARAM: Record<string, View> = { spiel: "game", game: "game", video: "video", zahlen: "numbers", numbers: "numbers" };
type Sub = "shots" | "keepers" | "physical" | "report";
// in the order of the match sheet: the overview, the record itself, shots, goalkeepers, then the
// physical load from the tracking
// the parts of Zahlen, in this order
const SUBS: Sub[] = ["report", "shots", "keepers", "physical"];


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

  // the tab and the thing live in the address (?tab=spiel|video|zahlen&thing=n): reload keeps
  // them and «Zurück» goes back to the previous tab; a match opens on Spiel
  const [view, setViewState] = useState<View>("game");
  const [thing, setThingState] = useState<number | null>(null);
  const linkedView = useRef(false);
  const readAddress = useCallback(() => {
    const q = new URLSearchParams(window.location.search);
    const v = VIEW_PARAM[q.get("tab") ?? ""];
    const n = Number(q.get("thing"));
    if (v) linkedView.current = true;
    setViewState(v ?? (q.get("t") ? "video" : "game"));
    setThingState(Number.isInteger(n) && n >= 1 && n <= 3 ? n : null);
  }, []);
  useEffect(() => {
    readAddress();
    window.addEventListener("popstate", readAddress);
    return () => window.removeEventListener("popstate", readAddress);
  }, [readAddress]);
  const TAB_WORD: Record<View, string> = { game: "spiel", video: "video", numbers: "zahlen" };
  const setView = useCallback((v: View, n: number | null = null) => {
    // a tab the coach chose is not changed by the default afterwards
    linkedView.current = true;
    setViewState(v);
    setThingState(n);
    const q = new URLSearchParams(window.location.search);
    q.set("tab", TAB_WORD[v]);
    if (n != null) q.set("thing", String(n));
    else q.delete("thing");
    q.delete("t");
    window.history.pushState(null, "", `${window.location.pathname}?${q.toString()}`);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [askPane, setAskPane] = useState<{ pane: "feedback" } | null>(null);
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
  const graphics = useMatchGraphics(orgId, initial.id);
  const [bench, setBench] = useState(false);
  const ta = useTranslations("anlauf");
  const thingText = useThingText();
  const own = ownName(teamName, shell?.org.name ?? teamName);
  const more = useRef<HTMLDetailsElement>(null);
  const roster = useRosterNames(orgId, match.team_id, match.season_id);
  const names = useMemo(
    () => Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, playerLabel(r.jersey_number, `${r.first_name} ${r.last_name}`)])),
    [roster.data],
  );

  const jobs = match.jobs.map((j) => ({ ...j, ...live[j.id] }) as Job);
  const main = match.videos.find((v) => v.role === "main" && v.status === "ready");
  // without counted events the record, shots and goalkeepers have nothing to show: no dead tabs
  // (the overview says how they come: the match report or marking courtside)
  const counted = (stats.data?.quality.events ?? 0) > 0;
  // Zahlen: the figure sheets stacked, one level; running distance only with a video
  // running figures only from the tracking of a video, and called estimated (UX test Z5)
  const numberParts = (counted || stats.isLoading ? SUBS : SUBS.filter((v) => v === "physical")).filter((v) => v !== "physical" || main);
  const showPhysical = () => {
    setView("numbers");
    requestAnimationFrame(() => {
      document.querySelector("[data-testid=numbers-more]")?.setAttribute("open", "");
      document.getElementById("numbers-physical")?.scrollIntoView({ block: "start" });
    });
  };
  // a match opens on Spiel; one without video and events on Video, where the upload is
  const opened = useRef(false);
  const hasEvents = (stats.data?.own.shots ?? 0) + (stats.data?.opponent.shots ?? 0) > 0;
  useEffect(() => {
    if (opened.current || !stats.data) return;
    opened.current = true;
    // without video and without events the upload is the only thing to do: it sits on Video
    if (!linkedView.current && !new URLSearchParams(window.location.search).get("t")) setViewState(main || hasEvents ? "game" : "video");
  }, [stats.data, main, hasEvents]);
  const pendingVideos = match.videos.filter((v) => v.status !== "ready");
  const kickoff = new Date(match.kickoff_at);
  const result = match.opponent && match.score_own != null && match.score_opponent != null ? (match.score_own > match.score_opponent ? "won" : match.score_own < match.score_opponent ? "lost" : "draw") : null;
  const soon = kickoff.getTime() > Date.now() - 3 * 3600_000;
  const liveFirst = staff && match.score_own == null && !main && soon && match.source !== "paper_report";
  const uploadFirst = staff && !main && !liveFirst && match.source !== "paper_report";
  const running = jobs.filter((j) => j.status !== "succeeded");
  // RSVP belongs to "Teamfunktionen" (ADR 029): hidden while the team has them off
  const teamFeatures = shell?.teams.find((x) => x.id === match.team_id)?.team_features ?? false;

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
    setBench(true);
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
  const club: [string, string | null] = [shell?.org.primary_color ?? DEFAULT_CLUB, shell?.org.secondary_color ?? null];
  const oppKit = match.opponent_colors ? [match.opponent_colors.color, match.opponent_colors.second ?? null] : null;
  const checks = graphics.data?.checks.length ?? 0;
  // the stage of the tab Video (SPEC 7.3) once there are goals to show on it
  const stage = Boolean(main && graphics.data && graphics.data.goals.some((g) => g.has_video || g.source === "demo"));
  const confirmedGoals = graphics.data?.goals.filter((g) => g.confirmed).length ?? 0;
  const sourceParts = [
    main ? ta("sourceVideo") : null,
    (graphics.data?.report_goals.length ?? 0) > 0 ? ta("sourceReport") : null,
    graphics.data && graphics.data.goals.length > 0 ? ta("sourceMarked", { n: confirmedGoals, total: graphics.data.goals.length }) : null,
  ].filter(Boolean);
  return (
    <div className="space-y-8" style={matchStyle(club, oppKit) as CSSProperties}>
      <MatchHead match={match} ownName={own} oppName={oppName(match)} view={view} graphics={graphics.data}>
        {staff && match.opponent && !match.opponent_colors && <AskColour orgId={orgId} matchId={match.id} opponent={oppName(match)} />}
        {/* a known colour can be changed right in the head, five shirts (UX test B31) */}
        {staff && match.opponent && match.opponent_colors && (
          <details className="mt-2.5 text-sm font-bold" data-testid="change-colour">
            <summary className="inline-flex min-h-11 cursor-pointer list-none items-center gap-2 underline decoration-[1.5px] underline-offset-4 [&::-webkit-details-marker]:hidden">
              <i aria-hidden className="block size-5 border-[1.5px] border-club-ink" style={{ background: match.opponent_colors.color ?? undefined }} />
              {ta("changeColour", { opponent: oppName(match) })}
            </summary>
            {/* on the ground colour: the line of the match runs underneath */}
            <div className="mt-1 inline-block bg-ground px-3 pb-1 text-ink">
              <AskColour orgId={orgId} matchId={match.id} opponent={oppName(match)} />
            </div>
          </details>
        )}
      </MatchHead>
      {(justDone || ["uploading", "processing", "failed"].includes(match.status)) && (
        <p role="status" className="-mt-4 flex flex-wrap items-center gap-3 text-[15px] font-bold">
          {justDone && (
            <span className="inline-flex items-center gap-1.5">
              <Check aria-hidden className="size-4" />
              {t("processing.done")}
            </span>
          )}
          {["uploading", "processing", "failed"].includes(match.status) && <span className={match.status === "failed" ? "text-loss" : undefined}>{t(`matches.status_${match.status}`)}</span>}
        </p>
      )}
      <div className="space-y-6">
        {/* on a phone the actions sit above the three tabs, so «Zahlen» is never cut off */}
        <div className="flex flex-wrap-reverse items-end justify-between gap-x-3 border-b-2 border-ink">
          <Segmented<View>
            className="min-w-0 max-sm:w-full"
            variant="underline"
            label={t("tabs.video")}
            value={view}
            onChange={(v) => setView(v)}
            items={[
              { value: "game", label: t("tabs.game") },
              { value: "video", label: t("tabs.video") },
              { value: "numbers", label: t("tabs.numbers") },
            ]}
          />
          <div className="flex flex-wrap items-center justify-end gap-2 pb-2.5">
            {staff && checks > 0 && (
              <Link href={`${base}/check`} className="font-slant flex min-h-11 items-center gap-2 px-2 text-xl text-ink no-underline" data-testid="check-link">
                {ta("check")}
                <em className="grid h-[30px] min-w-[30px] place-items-center bg-attn px-1 font-sans text-base font-extrabold text-attn-ink not-italic">{checks}</em>
              </Link>
            )}
            {liveFirst && (
              <Link href={`${base}/matchday`} className={buttonClass("primary")} data-testid="live-link">
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
              {/* a word, not only the dots (UX test H09) */}
              <MenuTrigger className={buttonClass("secondary")} data-testid="match-menu">
                <MoreHorizontal aria-hidden />
                {t("common.more")}
              </MenuTrigger>
              <MenuContent>
                <MenuItem href={`/v1/orgs/${orgId}/matches/${match.id}/report.pdf?lang=${locale}`} external icon={<FileDown />} testId="pdf">
                  {t("matches.pdf")}
                </MenuItem>
                {/* the match card is «Als Bild für den Chat» in Tab Spiel now; the Spieltag only
                    before the result is in; the preparation lives in «Gegner» (UX test B35) */}
                {staff && !liveFirst && match.score_own == null && (
                  <MenuItem href={`${base}/matchday`} icon={<Radio />} testId="live-link">
                    {t("live.open")}
                  </MenuItem>
                )}
                {staff && match.score_own == null && (
                  <MenuItem href={`${base}/matchday?mode=marks`} icon={<Hand />} testId="marks-link">
                    {t("marks.title")}
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

      {sourceParts.length > 0 && (
        <div className="-mt-6 flex flex-wrap items-center gap-x-3.5 gap-y-1 text-[15px] text-ink-2 md:text-[15px]" data-testid="source-line">
          {ta("sources")}: {sourceParts.join(" · ")}
          <details className="inline">
            <summary className="cursor-pointer font-bold text-ink underline decoration-[1.5px] underline-offset-4">{ta("howCounted")}</summary>
            <span className="mt-1 block max-w-[66ch] text-ink-2">{ta("howCountedText")}</span>
          </details>
        </div>
      )}

      {/* who is coming: the players' replies, from before the match until shortly after it */}
      {staff && teamFeatures && match.kind !== "training" && Date.parse(match.kickoff_at) > Date.now() - 6 * 3600_000 && (
        <details className="group border-y border-foreground/15 py-3" data-testid="match-attendance">
          <summary className="cursor-pointer list-none font-semibold [&::-webkit-details-marker]:hidden">
            {t("matches.attendance")}
            <span className="ml-2 text-sm font-normal text-muted group-open:hidden">{t("matches.attendanceHint")}</span>
          </summary>
          <div className="mt-3">
            <AttendancePanel orgId={orgId} kind="match" id={match.id} />
          </div>
        </details>
      )}
      {running.length > 0 && <Processing jobs={jobs} orgId={orgId} staff={staff} onOtherFile={() => (setView("video"), requestAnimationFrame(() => document.getElementById("upload")?.scrollIntoView({ behavior: "smooth" })))} />}

      <div hidden={view !== "video"} className="space-y-6">
        {/* a player's own scenes of this match, one step away */}
        {!staff && <MyScenesLine orgId={orgId} matchId={match.id} />}
        {stage && main && graphics.data && (
          <VideoStage
            orgId={orgId}
            match={match}
            video={main}
            graphics={graphics.data}
            ownName={own}
            oppName={oppName(match)}
            staff={staff}
            thing={thing}
            onThing={(n) => setView("video", n)}
            onBench={() => setBench(true)}
          />
        )}
        {main ? (
          // with the stage, the workbench (events, defence systems, comments, feedback) is behind
          // «Mehr»; it stays mounted, so jumps from the other tabs still reach its player
          <section hidden={stage && !bench} aria-labelledby="bench-title" className={cn(stage && "border-t-2 border-ink pt-6")}>
            {stage && (
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 id="bench-title" className="text-[26px]">
                  {ta("bench")}
                </h2>
                <Button variant="secondary" size="sm" onClick={() => setBench(false)}>
                  {ta("benchClose")}
                </Button>
              </div>
            )}
            <Workspace orgId={orgId} match={match} video={main} staff={staff} teamName={teamName} oppName={oppName(match)} names={names} handle={player} setup={setup} requestPane={askPane} checkSteps={false} />
          </section>
        ) : !staff ? (
          <EmptyState icon={<Clapperboard />} title={match.source === "paper_report" ? t("stats.noVideo") : t("player.notReady")} />
        ) : null}
        {staff && !main && (
          <section id="upload" className="scroll-mt-24 space-y-4" aria-label={t("upload.title")}>
            <p className="m-0 max-w-[60ch] text-[17px] font-bold">{ta("noVideoBlock")}</p>
            <UploadPanel orgId={orgId} matchId={match.id} onUploaded={() => void qc.invalidateQueries({ queryKey: key })} />
          </section>
        )}
        <PartsPanel orgId={orgId} matchId={match.id} staff={staff} />
        {!main && match.videos.map((v) => v.quality_report && <QualityReport key={v.id} video={v} />)}
      </div>

      {view === "game" && (
        <div className="animate-fade space-y-10">
          {/* a match without video: the report's facts below, the way to the video on top */}
          {!main && staff && (
            <section className="space-y-3 border-2 border-dashed border-ink/40 p-4 md:p-6" data-testid="no-video">
              <h2 className="text-[26px]">{ta("noVideoTitle")}</h2>
              <p className="m-0 max-w-[60ch] text-[17px]">{ta("noVideoBlock")}</p>
              <Button onClick={() => setView("video")}>{ta("chooseVideo")}</Button>
            </section>
          )}
          {graphics.data && graphics.data.goals.length > 0 && (
            <ThreeThingsView orgId={orgId} matchId={match.id} graphics={graphics.data} oppName={oppName(match)} onScenes={main ? (_, n) => setView("video", n) : undefined} />
          )}
          <GameActions
            collect={staff && counted && match.opponent ? <FromMatchButton orgId={orgId} teamId={match.team_id} matchId={match.id} opponent={oppName(match)} /> : null}
            onHighlights={() => {
              if (more.current) more.current.open = true;
              requestAnimationFrame(() => document.getElementById("highlights")?.scrollIntoView({ behavior: "smooth", block: "start" }));
            }}
            onPicture={
              match.score_own != null && match.score_opponent != null
                ? () =>
                    staff && match.opponent
                      ? void downloadCard()
                      : chatPicture({
                      title: `${own} ${ta("vsShort")} ${oppName(match)}`,
                      sub: [format.dateTime(new Date(match.kickoff_at), { dateStyle: "long" }), match.venue].filter(Boolean).join(" · "),
                      score: `${match.score_own}:${match.score_opponent}`,
                      heading: ta("chatHeading"),
                      things: graphics.data ? threeThings(goalRuns(graphics.data)).map((x) => ({ value: x.value, text: thingText(x) })) : [],
                      file: `${oppName(match)}-${match.score_own}-${match.score_opponent}.png`.replace(/\s+/g, "-"),
                    })
                : undefined
            }
          />
          <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_340px]">
            <div className="min-w-0 space-y-10">
              {graphics.data && <PointOpen orgId={orgId} matchId={match.id} graphics={graphics.data} oppName={oppName(match)} />}
              <Telegram
                match={{ own, opp: oppName(match), score: match.score_own != null && match.score_opponent != null ? [match.score_own, match.score_opponent] : null, half: match.halftime_own != null && match.halftime_opponent != null ? [match.halftime_own, match.halftime_opponent] : null, venue: match.venue ?? null, periodS: match.period_s, periods: match.periods }}
                stats={stats.data ?? null}
                names={names}
              />
            </div>
            <div className="space-y-10">
              {graphics.data && graphics.data.goals.length > 0 && <MatchZones graphics={graphics.data} />}
              {stats.data && <ThreeFigures stats={stats.data} names={names} />}
            </div>
          </div>
          {/* everything else of the match, as before, one step away (UX test B08) */}
          <details ref={more} className="group border-t-2 border-ink pt-4" data-testid="game-more">
            <summary className="flex min-h-11 cursor-pointer list-none items-baseline gap-3 [&::-webkit-details-marker]:hidden">
              <span className="font-slant text-[22px]">{ta("moreGame")}</span>
              <span className="text-[15px] text-ink-2 group-open:hidden">{ta("moreGameHint")}</span>
            </summary>
            <div className="mt-8 space-y-10">
          {stats.data && stats.data.quality.events > 0 ? (
            <div className="space-y-10">
              <OverviewView orgId={orgId} match={match} teamName={teamName} stats={stats.data} names={names} staff={staff} onPlay={main ? onPlay : undefined} videoNote={videoNote} />
              <ConcededByPosition stats={stats.data} />
              {/* what the video itself shows (possession, attacks) belongs to the match too */}
              {main && (
                <VideoOverview
                  orgId={orgId}
                  matchId={match.id}
                  teamId={match.team_id}
                  ownName={own}
                  oppName={oppName(match)}
                  durationMs={main.duration_s ? main.duration_s * 1000 : null}
                  kickoff={match.kickoff_ms}
                  periodS={match.period_s}
                  onPlay={onPlay}
                  onPhysical={showPhysical}
                  staff={false}
                  compact
                />
              )}
            </div>
          ) : stats.isLoading ? (
            <Skeleton className="h-64" />
          ) : main ? (
            <VideoOverview
              orgId={orgId}
              matchId={match.id}
              teamId={match.team_id}
              ownName={own}
              oppName={oppName(match)}
              durationMs={main.duration_s ? main.duration_s * 1000 : null}
              kickoff={match.kickoff_ms}
              periodS={match.period_s}
              onPlay={onPlay}
              onPhysical={showPhysical}
              staff={staff}
            />
          ) : (
            <EmptyState icon={<ChartNoAxesColumn />} title={t("stats.noData")}>
              {staff && match.source !== "paper_report" ? t("stats.noDataHint") : null}
            </EmptyState>
          )}
          <div className="space-y-8">
            {staff && main && (
              // feedback on the players' scenes happens beside the player in the video tab
              <FeedbackSummary orgId={orgId} matchId={match.id} onOpen={() => (setView("video"), setAskPane({ pane: "feedback" }))} />
            )}
            <div id="highlights" className="scroll-mt-24"><HighlightsView orgId={orgId} matchId={match.id} teamId={match.team_id} staff={staff} names={names} /></div>
            {staff && !main && <TeamFeedView orgId={orgId} matchId={match.id} kickoff={match.kickoff_ms} periodS={match.period_s} />}
            {staff && <MarksPanel orgId={orgId} matchId={match.id} onPlay={main ? onPlay : undefined} />}
          </div>
            </div>
          </details>
        </div>
      )}

      {view === "numbers" && (
        <div className="animate-fade">
          <NumbersView stats={stats.data ?? null} graphics={graphics.data ?? null} roster={roster.data ?? []} orgId={orgId} match={match} names={names} onPlay={main ? onPlay : undefined}>
          {graphics.data && graphics.data.goals.length > 0 && <MatchZones graphics={graphics.data} row />}
          {numberParts.length === 0 && (
            <EmptyState icon={<ChartNoAxesColumn />} title={t("stats.noData")}>
              {staff && match.source !== "paper_report" ? t("stats.noDataHint") : null}
            </EmptyState>
          )}
          {numberParts.map((part) => (
            <section key={part} id={`numbers-${part}`} aria-labelledby={`numbers-${part}-title`} className="scroll-mt-24 space-y-4">
              <h2 id={`numbers-${part}-title`} className="text-2xl">
                {t(`tabs.${part}`)}
              </h2>
              {part === "physical" ? (
                <PhysicalView
                  orgId={orgId}
                  matchId={match.id}
                  names={names}
                  teamName={teamName}
                  oppName={oppName(match)}
                  videoNote={videoNote}
                  short={covers != null && covers.reduce((s, c) => s + c.to - c.from, 0) < match.period_s}
                />
              ) : stats.data ? (
                (() => {
                  const props = { orgId, match, teamName, stats: stats.data, names, staff, onPlay: main ? onPlay : undefined };
                  if (part === "report") return <ReportView {...props} />;
                  if (part === "keepers") return <KeepersView {...props} />;
                  return <ShotsView {...props} />;
                })()
              ) : (
                <Skeleton className="h-40" />
              )}
            </section>
          ))}
          </NumbersView>
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

function Processing({ jobs, orgId, staff, onOtherFile }: { jobs: Job[]; orgId: string; staff: boolean; onOtherFile?: () => void }) {
  const t = useTranslations("processing");
  const ta = useTranslations("anlauf");
  const now = useNow({ updateInterval: 5000 });
  const running = jobs.filter((j) => j.status !== "succeeded");
  const failed = running.find((j) => j.status === "failed");
  const ingest = jobs.find((j) => j.kind === "ingest");
  const analysis = jobs.find((j) => j.kind === "analysis");
  // three steps in the coach's words (UX test B11): the video read, the players followed, the
  // three things searched; the technical stages stay one step away
  const state = (done: boolean, active: boolean) => (done ? "done" : active ? "running" : "pending");
  const ingestDone = ingest?.status === "succeeded" || Boolean(analysis);
  const followDone = analysis?.status === "succeeded" || (analysis?.progress ?? 0) >= 0.7;
  const steps = [
    { key: "read", st: state(ingestDone, Boolean(ingest) && !ingestDone) },
    { key: "follow", st: state(followDone, Boolean(analysis) && !followDone) },
    { key: "things", st: state(analysis?.status === "succeeded", followDone && analysis?.status !== "succeeded") },
  ] as const;
  const current = analysis && analysis.status !== "succeeded" ? analysis : (ingest ?? running[0]);
  // the bar only moves forward (UX test H05: it jumped 10, 15, 70, 5 between the stages): the
  // whole run counts, ingest the first fifth, the analysis the rest
  const overall = analysis ? 0.2 + 0.8 * (analysis.status === "succeeded" ? 1 : analysis.progress) : 0.2 * (ingest?.progress ?? 0);
  const shown = useRef(0);
  shown.current = Math.max(shown.current, overall);
  const started = current?.started_at ? new Date(current.started_at).getTime() : null;
  const elapsed = started ? (now.getTime() - started) / 1000 : 0;
  const etaMin = current && current.status === "running" && current.progress > 0.05 && elapsed > 20 ? Math.max(1, Math.round(((elapsed / current.progress) * (1 - current.progress)) / 60)) : null;
  if (failed) {
    // what failed, what stays, what to do (UX test B29)
    return (
      <section className="space-y-3 border-2 border-loss p-4 md:p-6" role="alert" data-testid="job-failed" data-orgid={orgId}>
        <h2 className="text-[26px]">{t("failedTitle")}</h2>
        <p className="m-0 max-w-[60ch] text-[17px]">{t("failedText")}</p>
        {staff && onOtherFile && (
          <button type="button" className={buttonClass("primary")} onClick={onOtherFile}>
            {t("otherFile")}
          </button>
        )}
      </section>
    );
  }
  return (
    // Analyse läuft (SPEC 7.13): the steps with fertig / läuft / danach, a bar, the minutes left,
    // something useful meanwhile and the three fields that will fill
    <section className="grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" aria-live="polite" data-testid="job" data-orgid={orgId} data-staff={staff || undefined}>
      <div>
        <h2 className="text-[26px]">{ta("titleRunning")}</h2>
        <div className="mt-3 h-1.5 bg-rule" aria-hidden>
          <div className="h-full bg-ink transition-all duration-500" style={{ width: `${shown.current * 100}%` }} />
        </div>
        <p className="mt-2 text-[15px] font-bold">{etaMin != null ? ta("minutesLeft", { minutes: etaMin }) : t("etaSoon")}</p>
        <ol className="mt-4 m-0 list-none p-0">
          {steps.map(({ key, st }) => (
            <li key={key} className={cn("grid min-h-11 grid-cols-[72px_minmax(0,1fr)] items-baseline gap-3 border-t border-rule py-2.5 text-base", st === "pending" && "text-ink-2")}>
              <span className={cn("justify-self-start text-[15px] font-bold", st === "done" ? "text-win" : st === "running" ? "bg-attn px-1.5 py-0.5 text-attn-ink" : "text-ink-2")}>
                {st === "done" ? ta("stepDone") : st === "running" ? ta("stepRunning") : ta("stepNext")}
              </span>
              {t(`coach_${key}`)}
            </li>
          ))}
        </ol>
        <p className="mt-4 text-[15px] text-ink-2">{ta("meanwhile")}</p>
        <details className="mt-3 text-[15px] text-ink-2">
          <summary className="min-h-11 cursor-pointer content-center font-semibold">{t("technical")}</summary>
          {running.map((j) => (
            <ul key={j.id} className="m-0 list-none p-0">
              {Object.entries((j.stages ?? {}) as Record<string, { status?: string }>).map(([k, v]) => (
                <li key={k}>
                  {t.has(`stage_${j.kind}_${k}`) ? t(`stage_${j.kind}_${k}` as "stage_download") : t.has(`stage_${k}`) ? t(`stage_${k}` as "stage_download") : k}: {v?.status ?? "pending"}
                </li>
              ))}
            </ul>
          ))}
        </details>
      </div>
      <div className="grid grid-cols-3 gap-3 self-start" aria-hidden>
        {[0, 1, 2].map((i) => (
          <EmptyField key={i} />
        ))}
      </div>
    </section>
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


"use client";

import { checkMinutes, spotCounts } from "@/lib/shot-spot";
import { nextTask } from "@/lib/next-task";
import { ShareButton, shareMatchCard } from "@/components/sharing/share-button";
import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from "react";
import Link from "next/link";
import { useEscape } from "@/lib/use-escape";
import { ArrowLeftRight, Check, ChevronDown, ChartNoAxesColumn, Clapperboard, FileDown, Hand, Info, MoreHorizontal, Pencil, Plus, Radio, Shield, Trash2 } from "lucide-react";
import { MatchSidesProvider, useMatchRoster } from "@/components/domain/match-sides";
import { RosterNumberHint } from "@/components/roster/number-hint";
import { homeFirst, matchSides, type MatchSides } from "@/lib/match-sides";
import { courseOf } from "@/lib/score-flow";
import { DEFAULT_CLUB, matchStyle } from "@/lib/color";
import { markOpened } from "@/lib/fresh-match";
import { checkCount, furtherMoments, goalRuns, useMatchGraphics } from "@/lib/graphics";
import { ownName } from "@/lib/own-name";
import { ThreeThingsView } from "@/components/anlauf/three-things-view";
import { ExampleBanner } from "@/components/anlauf/example-banner";
import { MatchHead } from "./match-head";
import { NextTaskLine } from "./next-task";
import { AskColour } from "./ask-colour";
import { VideoStage } from "./video-stage";
import type { Kits } from "@/lib/kit";
import { playerLabel } from "@/lib/player-name";
import { useOptionalShell } from "@/components/shell/context";
import { EmptyState, Skeleton } from "@/components/ui/card";
import { useConfirm } from "@/components/ui/confirm";
import { Dialog } from "@/components/ui/dialog";
import { MenuContent, MenuItem, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { Segmented } from "@/components/ui/tabs";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import { FromMatchButton } from "@/components/collections/from-match";
import { GameActions, PointOpen, Telegram, ThreeFigures } from "./game-tab";
import { TodayBlock } from "./today-block";
import { OverviewView, ReportView, ShotsView, useStats } from "./analysis-views";
import dynamic from "next/dynamic";
import { Button, buttonClass } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { isMatchDay } from "@/lib/match-day";
import { MATCHDAY_OFFERED } from "@/lib/features";
import { cn } from "@/lib/utils";
import { useOpponentName } from "@/lib/opponent";
import { formatClock } from "@/lib/format";
import { coverage } from "@/lib/match-workflow";
import { MyScenesLine } from "./feed-views";
import { officialGoalsKey } from "./official-goals";
import { PartsLine, PartsPanel, usePartMarkers } from "./parts-panel";
import type { Pane } from "./work-rail";
import { AnalysisNotice } from "@/components/analysis/analysis-notice";
import { latestJobs, partsOf, timelineVideo } from "@/lib/video-parts";
import { isActive, progressKey, useProgress, withLocal } from "@/lib/progress";
import { useLocalUploads } from "@/lib/upload-store";
import { storedUploadIds } from "@/lib/upload";

// Loaded when shown, so the match page stays within the bundle budget (scripts/check-bundle.mjs).
// Keepers and running distances sit deep in the Zahlen tab.
// panels that only show in some states load on demand in the browser (bundle budget,
// scripts/check-bundle.mjs; rendered on the server their useId values did not match)
const Workspace = dynamic(() => import("./workspace").then((m) => m.Workspace), { ssr: false, loading: () => <Skeleton className="h-64" /> });
const KitFields = dynamic(() => import("@/components/domain/kit-fields").then((m) => m.KitFields), { ssr: false });
const NextOpponent = dynamic(() => import("@/app/app/[orgId]/teams/[teamId]/matches/start-view").then((m) => m.NextOpponent), { ssr: false });
const AttendancePanel = dynamic(() => import("@/components/team/attendance-panel").then((m) => m.AttendancePanel), { ssr: false });
const UploadPanel = dynamic(() => import("./upload-panel").then((m) => m.UploadPanel), { ssr: false });
const ProgressPanel = dynamic(() => import("@/components/progress/progress-panel").then((m) => m.ProgressPanel), { ssr: false });
const KnownFacts = dynamic(() => import("./known-facts").then((m) => m.KnownFacts), { ssr: false });
const AttachmentsPanel = dynamic(() => import("./attachments-panel").then((m) => m.AttachmentsPanel), { ssr: false });
const KeepersView = dynamic(() => import("./m5-views").then((m) => m.KeepersView));
const PhysicalView = dynamic(() => import("./m5-views").then((m) => m.PhysicalView));
// the Zahlen tab, the highlights, the match-day marks and the exchange: not on the first screen
const NumbersView = dynamic(() => import("./numbers-view").then((m) => m.NumbersView));
// client only: it sits in the closed «Mehr zum Spiel», and rendered on the server its form fields
// got other useId values than in the browser (hydration warning on every match page)
const HighlightsView = dynamic(() => import("./highlight-views").then((m) => m.HighlightsView), { ssr: false });
const MarksPanel = dynamic(() => import("./marks-panel").then((m) => m.MarksPanel));
const ExchangePanel = dynamic(() => import("./exchange-panel").then((m) => m.ExchangePanel));

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


export function MatchView({ orgId, initial, teamName, staff, canDelete = staff }: { orgId: string; initial: Match; teamName: string; staff: boolean; /** players work with the video but do not delete (K18) */ canDelete?: boolean }) {
  const t = useTranslations();
  const oppName = useOpponentName();
  const locale = useLocale();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const router = useRouter();
  const shell = useOptionalShell();
  const key = ["match", initial.id];
  // opened after its analysis is done: the start's head goes back to the last match once the
  // questions are answered (real-video test, second round)
  const analysed = useMatchGraphics(orgId, initial.id).data?.analysis === "ready";
  useEffect(() => {
    if (analysed) markOpened(initial.id);
  }, [analysed, initial.id]);
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
      // the progress block reads the API's progress (steps, time left): fresh on every report
      void qc.invalidateQueries({ queryKey: progressKey(orgId) });
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
  // one goal's scene from the Spiel tab (?scene=eventId): the Video tab opens at it
  const [scene, setScene] = useState<string | null>(null);
  const linkedView = useRef(false);
  // ?mark=court (the strip's «Spielfeld markieren»): opened once the page knows its video
  const [markCourtLink, setMarkCourtLink] = useState(false);
  const readAddress = useCallback(() => {
    const q = new URLSearchParams(window.location.search);
    const v = VIEW_PARAM[q.get("tab") ?? ""];
    const n = Number(q.get("thing"));
    if (v) linkedView.current = true;
    setViewState(v ?? (q.get("t") ? "video" : "game"));
    setThingState(Number.isInteger(n) && n >= 1 && n <= 3 ? n : null);
    setScene(q.get("scene"));
    if (q.get("mark") === "court") {
      // once: the address loses it, so a reload or «Zurück» does not open the dialog again
      q.delete("mark");
      window.history.replaceState(null, "", `${window.location.pathname}?${q.toString()}`);
      setMarkCourtLink(true);
    }
  }, []);
  useEffect(() => {
    readAddress();
    window.addEventListener("popstate", readAddress);
    return () => window.removeEventListener("popstate", readAddress);
  }, [readAddress]);
  // a link to this page with another address (the frame's «Video hochladen» on a match without
  // video, A11): the tab follows it, and #upload brings the field into view
  const address = useSearchParams().toString();
  useEffect(() => {
    readAddress();
    if (window.location.hash === "#upload") requestAnimationFrame(() => requestAnimationFrame(() => document.getElementById("upload")?.scrollIntoView({ behavior: "smooth" })));
  }, [address, readAddress]);
  const TAB_WORD: Record<View, string> = { game: "spiel", video: "video", numbers: "zahlen" };
  const setView = useCallback((v: View, n: number | null = null, sceneId: string | null = null) => {
    // a tab the coach chose is not changed by the default afterwards
    linkedView.current = true;
    setViewState(v);
    setThingState(n);
    setScene(sceneId);
    const q = new URLSearchParams(window.location.search);
    q.set("tab", TAB_WORD[v]);
    if (n != null) q.set("thing", String(n));
    else q.delete("thing");
    if (sceneId) q.set("scene", sceneId);
    else q.delete("scene");
    q.delete("t");
    window.history.pushState(null, "", `${window.location.pathname}?${q.toString()}`);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [askPane, setAskPane] = useState<{ pane: Pane } | null>(null);
  // «Spielfeld markieren» (progress block, strip link ?mark=court): the workbench opens at the
  // court step and the marking dialog opens as soon as the hall image is there (#141)
  const [markAsk, setMarkAsk] = useState<{ n: number } | null>(null);
  const markCourt = useCallback(() => {
    setView("video");
    setBench(true);
    setAskPane({ pane: "court" });
    setMarkAsk({ n: Date.now() });
  }, [setView]);
  useEffect(() => {
    if (!markCourtLink) return;
    setMarkCourtLink(false);
    markCourt();
  }, [markCourtLink, markCourt]);
  const player = useRef<PlayerHandle | null>(null);
  const stats = useStats(orgId, initial.id);
  const graphics = useMatchGraphics(orgId, initial.id);
  const [bench, setBench] = useState(false);
  // «Zeichnen» on the stage: the workbench opens drawing on the stage's moment (app review BUG-13)
  const [drawAt, setDrawAt] = useState<{ t_ms: number } | null>(null);
  useEffect(() => {
    if (!bench) setDrawAt(null);
  }, [bench]);
  // Escape closes the Werkbank like its «Schliessen» (A15)
  const benchRef = useRef<HTMLElement>(null);
  useEscape(bench, () => setBench(false), benchRef);
  // «So rechnen wir» beside the source line, opened by its info sign (A17)
  const [howOpen, setHowOpen] = useState(false);
  const howRef = useRef<HTMLParagraphElement>(null);
  useEscape(howOpen, () => setHowOpen(false), howRef);
  // deep links (?t=ms), e.g. a scene from Szenen or a play drawn on a video moment: the moment
  // plays in the full player, so it opens (behind the stage it would seek out of sight)
  // a moment in the full player: it opens, and the moment is sought once the video can
  // the workbench and its player are mounted only while open: one video on the page, not a second
  // one loading hidden behind the stage (app review BUG-19); so a jump waits for its player
  const benchAt = useCallback((t0: number, play = false, show = false) => {
    setBench(true);
    const id = window.setInterval(() => {
      const v = player.current?.video();
      if (v && v.readyState >= 1) {
        player.current?.seek(t0);
        if (play) player.current?.play();
        if (show) reveal();
        window.clearInterval(id);
      }
    }, 300);
    const stop = window.setTimeout(() => window.clearInterval(id), 30_000);
    return () => (window.clearInterval(id), window.clearTimeout(stop));
  }, []);
  useEffect(() => {
    const t0 = Number(new URLSearchParams(window.location.search).get("t"));
    if (!Number.isFinite(t0) || t0 <= 0) return;
    return benchAt(t0);
  }, [benchAt]);
  const ta = useTranslations("anlauf");
  const tParts = useTranslations("parts");
  const plainPlayer = useRef<PlayerHandle>(null);
  // a video of the opponent against another team (K3): that team takes the own side
  const scouting = match.kind === "scouting";
  // the example match of «Demo-Spiel ansehen» is looked at, not worked on (R1, R22): no upload,
  // no colour question, no files, no placeholders; seeded demo matches with a video stay matches
  const example = match.source === "demo";
  // the one notion of perspective (BUG-01 to 07): our team, or both teams by name when observed
  const sides = matchSides(match, { team: ownName(teamName, shell?.org.name ?? teamName), opponent: oppName(match), otherFallback: t("progress.otherTeam") });
  const own = sides.own;
  // the other team of an observed match has a profile of its own when the club knows it as an
  // opponent (by name)
  const opponents = useQuery({
    queryKey: ["opponents", orgId],
    enabled: scouting && Boolean(match.scouting_other),
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/opponents", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const otherProfile = scouting ? opponents.data?.find((o) => o.name.trim().toLowerCase() === (match.scouting_other ?? "").trim().toLowerCase()) : undefined;
  const more = useRef<HTMLDetailsElement>(null);
  // the example names nobody of the team: its players are invented numbers, never the roster (A4)
  // an observed match names nobody of the team either: our roster plays no part in it (L4)
  const rosterQuery = useMatchRoster(orgId, match);
  const rosterRows = useMemo(() => (example ? [] : (rosterQuery.data ?? [])), [example, rosterQuery.data]);
  const names = useMemo(
    () => Object.fromEntries(rosterRows.map((r) => [r.player_id, playerLabel(r.jersey_number, `${r.first_name} ${r.last_name}`)])),
    [rosterRows],
  );

  const jobs = latestJobs(match.jobs.map((j) => ({ ...j, ...live[j.id] }) as Job));
  // the video the match plays: its first part, as long as all parts together (Q-VIDEO-PARTS)
  const main = timelineVideo(match.videos);
  const parts = partsOf(match.videos);
  const partMarkers = usePartMarkers(match.videos);
  // without counted events the record, shots and goalkeepers have nothing to show: no dead tabs
  // (the overview says how they come: the match report or marking courtside)
  const counted = (stats.data?.quality.events ?? 0) > 0;
  // scenes are goals with a place in the video: collections and highlights need them (review R34)
  const hasScenes = Boolean(graphics.data?.goals.some((g) => g.has_video || g.source === "demo"));
  // «Highlights teilen» only once there is a finished reel to share (app review UX-06); the same
  // query as the highlights section below
  const reels = useQuery({
    queryKey: ["highlights", match.id],
    enabled: staff && hasScenes,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/highlights", { params: { path: { org_id: orgId, match_id: match.id } } })).data ?? [],
  });
  const hasReels = (reels.data ?? []).some((r) => r.status === "ready");
  // a match still to come without a score: nothing to share or look back on yet
  const upcoming = !main && match.score_own == null && Date.parse(match.kickoff_at) > Date.now();
  // the Spielkarte, rendered on the server: into the chat by the share sheet, else saved (K20)
  const cardPicture =
    match.score_own != null && match.score_opponent != null
      ? () => shareMatchCard(orgId, match.id, `${t("share.card.file")}-${oppName(match)}-${match.score_own}-${match.score_opponent}.png`.replace(/\s+/g, "-"))
      : undefined;
  const telegram = (
    <Telegram
      match={{ own, opp: oppName(match), score: match.score_own != null && match.score_opponent != null ? [match.score_own, match.score_opponent] : null, half: match.halftime_own != null && match.halftime_opponent != null ? [match.halftime_own, match.halftime_opponent] : null, venue: match.venue ?? null, periodS: match.period_s, periods: match.periods }}
      stats={stats.data ?? null}
      names={names}
      roster={rosterRows}
    />
  );
  // a played match without video (not the example): what works today stands first (review R39)
  const today = !main && !example && !upcoming && (cardPicture != null || match.score_own != null);
  // Zahlen: the figure sheets stacked, one level; running distance only with a video
  // running figures only from the tracking of a video, and called estimated (UX test Z5)
  const numberParts = (counted || stats.isLoading ? SUBS : SUBS.filter((v) => v === "physical")).filter((v) => v !== "physical" || main);
  // a match opens on Spiel; one without video and events on Video, where the upload is
  const teamMatches = useQuery({
    queryKey: ["matches", match.team_id],
    enabled: Date.parse(match.kickoff_at) > Date.now(),
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/matches", { params: { path: { org_id: orgId, team_id: match.team_id } } })).data ?? [],
  });
  const opened = useRef(false);
  const hasEvents = (stats.data?.own.shots ?? 0) + (stats.data?.opponent.shots ?? 0) > 0;
  useEffect(() => {
    if (opened.current || !stats.data) return;
    opened.current = true;
    // without video and without events the upload is the only thing to do: it sits on Video; a
    // match still to be played opens on Spiel with the opponent and «Spieltag starten» (UX test N16)
    const ahead = new Date(match.kickoff_at).getTime() > Date.now();
    if (!linkedView.current && !new URLSearchParams(window.location.search).get("t")) setViewState(main || hasEvents || ahead ? "game" : "video");
  }, [stats.data, main, hasEvents, match.kickoff_at]);
  const pendingVideos = match.videos.filter((v) => v.status !== "ready");
  // «Spieltag starten» up front only on match day (from three hours before the kick-off); days
  // before it is a quiet action in the menu and below the opponent
  const matchDay = isMatchDay(match.kickoff_at);
  const liveFirst = staff && match.score_own == null && !main && matchDay && match.source !== "paper_report" && !example;
  const uploadFirst = staff && !main && !liveFirst && match.source !== "paper_report" && !example;
  // this match's upload field is the one way to upload from here: the frame's button leads to it
  const setPageUpload = shell?.setPageUpload;
  useEffect(() => {
    if (!setPageUpload || !uploadFirst) return;
    setPageUpload(`/app/${orgId}/matches/${match.id}?tab=video#upload`);
    return () => setPageUpload(null);
  }, [setPageUpload, uploadFirst, orgId, match.id]);
  // the progress of the uploads and the processing (K13, B4): the API's view, with the uploads of
  // this tab laid over; shown while it runs, and when something failed
  const local = useLocalUploads();
  // read after mount (the server knows no browser storage)
  const [stored, setStored] = useState<Set<string>>(() => new Set());
  useEffect(() => setStored(storedUploadIds()), [local]);
  const allProgress = useProgress(orgId);
  const listed = allProgress.data?.find((p) => p.match_id === match.id);
  const progress = withLocal(listed ? [listed] : match.progress ? [match.progress] : [], local, Date.now(), stored)[0] ?? null;
  const progressShown = progress != null && (isActive(progress) || progress.state === "failed");
  // the analysis is done, nothing open in Prüfen, no goal found and no result known (L6)
  const noGoals = Boolean(
    main && graphics.data?.analysis === "ready" && !graphics.data.goals.length && !graphics.data.checks.length && match.score_own == null && !progressShown,
  );
  // uploads the API holds as unfinished (not a link import): the upload panel offers the way on
  const stuckUploads = match.videos.filter((v) => v.status === "uploading" && progress?.files.find((f) => f.video_id === v.id)?.step !== "link");
  const ownKits = { own: match.kit_own, own_gk: match.kit_own_gk, opponent: match.kit_opponent, opponent_gk: match.kit_opponent_gk, referee: match.kit_referee ?? null };
  const official = useQuery({
    queryKey: ["official", match.team_id],
    enabled: staff,
    staleTime: 600_000,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/official", { params: { path: { org_id: orgId, team_id: match.team_id } } })).data ?? null,
  });
  // the «Weitere Datei» box stays open after the upload (with «Fertig hochgeladen») until closed
  const [addOpen, setAddOpen] = useState(false);
  const adding = pendingVideos.some((v) => v.status === "processing" || v.status === "uploading");
  useEffect(() => {
    if (adding) setAddOpen(true);
  }, [adding]);
  // RSVP belongs to "Teamfunktionen" (ADR 029): hidden while the team has them off
  const teamFeatures = shell?.teams.find((x) => x.id === match.team_id)?.team_features ?? false;

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

  // to the files of the match at the end of the tab Spiel
  function toAttachments() {
    setView("game");
    requestAnimationFrame(() => requestAnimationFrame(() => document.getElementById("attachments")?.scrollIntoView({ behavior: "smooth" })));
  }

  // to the upload of the tab Video (another file, or the same file again to go on)
  function toUpload() {
    setView("video");
    requestAnimationFrame(() => document.getElementById("upload")?.scrollIntoView({ behavior: "smooth" }));
  }

  function onPlay(ms: number) {
    setView("video");
    benchAt(ms, true, true);
  }

  const base = `/app/${orgId}/matches/${match.id}`;
  // what the video covers of the match, for the analysis to say which figures it can carry
  // the course of the match over what the data covers (BUG-20): the match minutes of the video, or
  // without a throw-off the video's own minutes (the goals then carry video times), never 0 to 60
  const courseSpan = courseOf(graphics.data ?? null, match.kickoff_ms, main?.duration_s ?? null);
  const covers = main ? coverage(match.kickoff_ms, match.period_s, main.duration_s ? main.duration_s * 1000 : null) : null;
  const videoNote = covers?.length
    ? t("workflow.coverage", { clip: covers.map((c) => `${formatClock(c.from * 1000)} ${t("workflow.to")} ${formatClock(c.to * 1000)}`).join(", ") })
    : null;
  // the main video is there: more cameras (goal cameras, a second angle) and the quality of the
  // recording belong to the court step of the workspace, not under every step
  const setup = main ? (
    <>
      {match.videos.map((v) => v.quality_report && <QualityReport key={v.id} video={v} />)}
    </>
  ) : null;
  const club: [string, string | null] = [shell?.org.primary_color ?? DEFAULT_CLUB, shell?.org.secondary_color ?? null];
  const oppKit = match.opponent_colors ? [match.opponent_colors.color, match.opponent_colors.second ?? null] : null;
  const checks = graphics.data ? checkCount(graphics.data) : 0;
  const further = graphics.data ? furtherMoments(graphics.data) : 0;
  // the stage of the tab Video (SPEC 7.3) once there are goals to show on it
  const stage = Boolean(main && graphics.data && graphics.data.goals.some((g) => g.has_video || g.source === "demo"));
  // «von dir bestätigt»: the goals a person confirmed (Prüfen, by hand), and of those how many have
  // their place («Von wo?»); not the estimated shot spot (Echtlauf 5 P5)
  const coachGoals = graphics.data?.goals.filter((g) => g.by_coach) ?? [];
  const placedGoals = coachGoals.filter((g) => g.zone != null && g.zone_source !== "unknown").length;
  const totalGoals = graphics.data?.goals.length ?? 0;
  const sourceParts = [
    main ? ta("sourceVideo") : null,
    graphics.data?.has_report ? ta("sourceReport") : null,
    coachGoals.length > 0
      ? `${coachGoals.length === totalGoals ? ta("sourceMarkedAll", { n: coachGoals.length }) : ta("sourceMarked", { n: coachGoals.length, total: totalGoals })}${ta("sourcePlaced", { n: placedGoals })}`
      : null,
  ].filter(Boolean);
  const sourceText = `${ta("sources")}: ${sourceParts.join(" · ")}`;
  const sourceCut = sourceText.lastIndexOf(" ") + 1;
  const [sourceHead, sourceTail] = [sourceText.slice(0, sourceCut), sourceText.slice(sourceCut)];
  return (
    <MatchSidesProvider sides={sides}>
    <div className="space-y-8" style={matchStyle(club, oppKit) as CSSProperties}>
      <MatchHead match={match} ownName={own} oppName={oppName(match)} view={view} graphics={graphics.data}>
        {staff && !example && match.opponent && !match.opponent_colors?.color && <AskColour orgId={orgId} matchId={match.id} opponent={oppName(match)} />}
        {/* a known colour can be changed right in the head, the eight shirts (UX test B31, A17) */}
        {staff && !example && match.opponent && match.opponent_colors?.color && (
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
      {example && <ExampleBanner orgId={orgId} teamId={match.team_id} />}
      {/* one clear next task on every match page (L5): open questions, missing shot spots, the video */}
      <NextTaskLine
        base={base}
        onUpload={toUpload}
        task={nextTask({
          staff,
          example,
          upcoming,
          hasOpponent: Boolean(match.opponent),
          running: progressShown || graphics.data?.analysis === "running",
          checks,
          spotsMissing: graphics.data ? spotCounts(graphics.data).missing : 0,
          hasVideo: Boolean(main),
          paper: match.source === "paper_report",
        })}
      />
      {/* one state at a time (L4): the progress block below says what runs; here only «fertig»
          and a failed match without progress to tell it */}
      {(justDone || (match.status === "failed" && !progressShown)) && (
        <p role="status" className="-mt-4 flex flex-wrap items-center gap-3 text-[15px] font-bold">
          {justDone && (
            <span className="inline-flex items-center gap-1.5">
              <Check aria-hidden className="size-4" />
              {t("processing.done")}
            </span>
          )}
          {match.status === "failed" && !progressShown && !justDone && <span className="text-loss">{t("matches.status_failed")}</span>}
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
          {/* on a 390 px phone Prüfen, Teilen and Mehr fit one line only with the smaller gap
              (UI check 20.11.: «Mehr» fell onto a line of its own) */}
          <div className="flex flex-wrap items-center justify-end gap-1 pb-2.5 sm:gap-2">
            {staff && checks > 0 && (
              <Link href={`${base}/check`} className="font-slant flex min-h-11 items-center gap-2 px-2 text-xl text-ink no-underline" data-testid="check-link">
                {ta("check")}
                <em className="grid h-[30px] min-w-[30px] place-items-center bg-attn px-1 font-sans text-base font-extrabold text-attn-ink not-italic">{checks}</em>
              </Link>
            )}
            {/* the main round answered, moments still wait behind «Mehr prüfen»: not rung, but
                reachable until answered (livegang L3: after leaving Prüfen they were gone) */}
            {staff && checks === 0 && further > 0 && (
              <Link href={`${base}/check`} aria-label={ta("checkFurtherLabel", { n: further })} className="font-slant flex min-h-11 items-center gap-2 px-2 text-xl text-ink no-underline" data-testid="check-further">
                {ta("check")}
                <span className="font-sans text-[15px] font-bold not-italic text-ink-2">{ta("checkFurther", { n: further })}</span>
              </Link>
            )}
            {MATCHDAY_OFFERED && liveFirst && (
              <Link href={`${base}/matchday`} className={buttonClass("primary")} data-testid="live-link">
                <Radio aria-hidden />
                {t("live.open")}
              </Link>
            )}
            {/* no own «Video hochladen» here: the frame's button leads to this match's field (A11) */}
            {/* before the match there is no report to share yet (UX test A05) */}
            {staff && !upcoming && (
              <ShareButton
                orgId={orgId}
                teamId={match.team_id}
                kind="match"
                targetId={match.id}
                info={{ title: oppName(match), team: own, opponent: oppName(match), score: match.score_own != null && match.score_opponent != null ? [match.score_own, match.score_opponent] : null }}
              />
            )}
            <MenuRoot>
              {/* a word, not only the dots (UX test H09) */}
              <MenuTrigger className={buttonClass("secondary", "md", "data-[state=open]:bg-ink data-[state=open]:text-ground")} data-testid="match-menu">
                <MoreHorizontal aria-hidden />
                {t("common.more")}
              </MenuTrigger>
              <MenuContent>
                <MenuItem href={`/v1/orgs/${orgId}/matches/${match.id}/report.pdf?lang=${locale}`} external icon={<FileDown />} testId="pdf">
                  {t("matches.pdf")}
                </MenuItem>
                {/* the match card is «Als Bild für den Chat» in Tab Spiel now; the Spieltag only
                    before the result is in; the preparation lives in «Gegner» (UX test B35) */}
                {MATCHDAY_OFFERED && staff && !liveFirst && match.score_own == null && (
                  <MenuItem href={`${base}/matchday`} icon={<Radio />} testId="live-link">
                    {t("live.open")}
                  </MenuItem>
                )}
                {MATCHDAY_OFFERED && staff && match.score_own == null && (
                  <MenuItem href={`${base}/matchday?mode=marks`} icon={<Hand />} testId="marks-link">
                    {t("marks.title")}
                  </MenuItem>
                )}
                {/* an observed match: the profile of each team that has one, both by name (BUG-07) */}
                {match.opponent && (
                  <MenuItem href={`/app/${orgId}/opponents/${match.opponent.id}`} icon={<Shield />}>
                    {scouting ? t("opponent.openOf", { name: match.opponent.name }) : `${t("opponent.open")}: ${match.opponent.name}`}
                  </MenuItem>
                )}
                {otherProfile && (
                  <MenuItem href={`/app/${orgId}/opponents/${otherProfile.id}`} icon={<Shield />}>
                    {t("opponent.openOf", { name: otherProfile.name })}
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
                {canDelete && <MenuSeparator />}
                {canDelete && (
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
        <div className="-mt-6 text-[15px] text-ink-2" data-testid="source-line">
          {/* «So rechnen wir» as the info sign right beside the source it explains (A17) */}
          {/* the sign stays with the last word, never alone on a line on the phone (UI check 20.11.) */}
          <p className="m-0">
            {sourceHead}
            <span className="whitespace-nowrap">
            {sourceTail}
            <button
              type="button"
              onClick={() => setHowOpen((v) => !v)}
              aria-expanded={howOpen}
              aria-controls="how-counted"
              aria-label={ta("howCounted")}
              title={ta("howCounted")}
              className="-my-3 inline-flex size-11 cursor-pointer items-center justify-center align-middle text-ink"
              data-testid="how-counted-open"
            >
              <Info aria-hidden className="size-5" strokeWidth={2.4} />
            </button>
            </span>
          </p>
          {howOpen && (
            <p id="how-counted" ref={howRef} className="m-0 mt-1 max-w-[66ch] border-l-4 border-rule pl-3 text-ink-2" data-testid="how-counted">
              <b className="text-ink">{ta("howCounted")}:</b> {graphics.data?.has_report ? ta("howCountedText") : ta("howCountedVideo")}
            </p>
          )}
        </div>
      )}

      {/* who is coming: the players' replies, from before the match until shortly after it; for the
          staff (coach rights, like deleting: K18) */}
      {canDelete && teamFeatures && match.kind !== "training" && Date.parse(match.kickoff_at) > Date.now() - 6 * 3600_000 && (
        <details className="group border-y border-foreground/15 py-3" data-testid="match-attendance">
          <summary className="flex min-h-11 cursor-pointer list-none items-center font-semibold [&::-webkit-details-marker]:hidden">
            {t("matches.attendance")}
            <span className="ml-2 text-sm font-normal text-muted group-open:hidden">{t("matches.attendanceHint")}</span>
          </summary>
          <div className="mt-3">
            <AttendancePanel orgId={orgId} kind="match" id={match.id} />
          </div>
        </details>
      )}
      {progressShown && progress && (
        <ProgressPanel
          orgId={orgId}
          progress={progress}
          staff={staff}
          canDelete={canDelete}
          onOtherFile={toUpload}
          onResumeUpload={toUpload}
          onRemoved={() => (void qc.invalidateQueries({ queryKey: key }), router.refresh())}
          onMarkCourt={staff && main ? markCourt : undefined}
          aside={
            // what is known and what comes, once the video is in (during the upload the way on counts)
            isActive(progress) && progress.stage !== "upload" ? (
              <KnownFacts orgId={orgId} match={match} ownName={own} oppName={oppName(match)} stats={stats.data ?? null} names={names} hasReport={graphics.data?.has_report ?? false} checks={checks} staff={staff} onAttach={toAttachments} />
            ) : undefined
          }
        />
      )}

      <div hidden={view !== "video"} className="space-y-6">
        {/* a player's own scenes of this match, one step away */}
        {!canDelete && <MyScenesLine orgId={orgId} matchId={match.id} />}
        {/* one video on the page: while the workbench is open its full player is the one, the stage
            (with its own player) waits; its scene stands in the address and comes back as it was.
            Both at once showed two players, and the e2e step after a goal tagged by hand found two
            whenever the goal had reached the stage */}
        {stage && main && graphics.data && !bench && (
          <VideoStage
            orgId={orgId}
            match={match}
            video={main}
            graphics={graphics.data}
            ownName={own}
            oppName={oppName(match)}
            staff={staff}
            thing={thing}
            scene={scene}
            onThing={(n) => setView("video", n)}
            onBench={() => setBench(true)}
            onDraw={(ms) => (setDrawAt({ t_ms: ms }), setBench(true))}
          />
        )}
        {/* the jump to the second half also with goals on the stage: it plays in the full player
            (the stage plays scenes only) */}
        {stage && main && graphics.data && !bench && <PartsLine videos={match.videos} onJump={(ms) => benchAt(ms, true)} />}
        {main && !stage && !bench && (
          // without goals on the stage: the video, one sentence, the way on; never the old capture
          // workbench by default (UX test N04), it opens with one tap
          <section className="space-y-4" data-testid="plain-stage">
            <VideoPlayer ref={plainPlayer} src={`/v1/orgs/${orgId}/videos/${main.id}/media/hls/master.m3u8`} markers={partMarkers} />
            <PartsLine videos={match.videos} onJump={(ms) => (plainPlayer.current?.seek(ms), plainPlayer.current?.play())} />
            {/* «fertig» only once the analysis is done, never while it runs (E06) */}
            {/* found too little to ask about: why and what helps (second round A6) */}
            {graphics.data?.analysis === "ready" && graphics.data.notice && !graphics.data.notice.failed ? (
              <AnalysisNotice notice={graphics.data.notice} cornersHref={staff && graphics.data.checks.some((c) => c.kind === "field") ? `${base}/check` : null} testId="plain-notice" />
            ) : (
              <p className="m-0 max-w-[60ch] text-[17px]">{graphics.data?.analysis === "running" ? ta("plainRunning") : graphics.data?.analysis !== "ready" ? ta("plainVideoOnly") : staff && checks > 0 ? ta("plainChecks", { n: checks }) : ta("plainNoGoals")}</p>
            )}
            <div className="flex flex-wrap gap-3">
              {/* with a notice its «Ecken setzen» is the way into Prüfen: not a second button */}
              {staff && checks > 0 && !(graphics.data?.analysis === "ready" && graphics.data.notice && !graphics.data.notice.failed) && (
                <Link href={`${base}/check`} className={buttonClass("primary")}>
                  {ta("plainToCheck")}
                </Link>
              )}
              {(
                <button type="button" onClick={() => setBench(true)} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4" data-testid="open-bench">
                  {staff ? ta("plainBench") : ta("plainComments")}
                </button>
              )}
            </div>
          </section>
        )}
        {main ? (
          // the workbench (events, defence systems, comments, feedback) is behind one tap, with or
          // without the stage; it stays mounted, so jumps from the other tabs still reach its player
          <section ref={benchRef} hidden={!bench} aria-labelledby="bench-title" className="border-t-2 border-ink pt-6">
            {(
              <div className="mb-4 flex items-center justify-between gap-3">
                {/* the workbench has one name, «Einrichten von Hand», and is reached only by it (L5) */}
                <div>
                  <h2 id="bench-title" className="text-[26px]">
                    {ta("bench")}
                  </h2>
                  {staff && <p className="m-0 text-[15px] text-ink-2">{ta("plainBenchHint")}</p>}
                </div>
                <Button variant="secondary" size="sm" onClick={() => setBench(false)}>
                  {ta("benchClose")}
                </Button>
              </div>
            )}
            <div className="mb-3">
              <PartsLine videos={match.videos} onJump={(ms) => benchAt(ms, true)} />
            </div>
            {bench && <Workspace orgId={orgId} match={match} video={main} staff={staff} teamName={own} oppName={oppName(match)} names={names} handle={player} setup={setup} requestPane={askPane} requestMark={markAsk} requestDraw={drawAt} checkSteps={false} />}
          </section>
        ) : !staff ? (
          <EmptyState icon={<Clapperboard />} title={match.source === "paper_report" ? t("stats.noVideo") : t("player.notReady")} />
        ) : null}
        {example && !main && (
          <p className="m-0 max-w-[60ch] text-[17px]" data-testid="demo-no-video">
            {ta("demoNoVideo")}
          </p>
        )}
        {staff && !example && !main && (
          <section id="upload" className="max-w-3xl scroll-mt-24 space-y-4" aria-label={t("upload.title")}>
            <p className="m-0 max-w-[60ch] text-[17px] font-bold">{ta("noVideoBlock")}</p>
            {/* before the first video: a squad with shirt numbers lets the analysis name people
                (audit #160); not for an observed match, whose people are not our squad */}
            {!scouting && !sides.neutral && <RosterNumberHint orgId={orgId} teamId={match.team_id} seasonId={match.season_id} />}
            {/* the field first (A11); the shirts after it, before «Mehr»: they are saved at once,
                also while the upload runs. The analysis separates the teams by their shirts:
                without the opponent's colour it guesses worse, so it is asked with the reason (E09) */}
            <UploadPanel
              orgId={orgId}
              matchId={match.id}
              kits={scouting ? null : ownKits}
              stuck={stuckUploads}
              progressFiles={progress?.files ?? []}
              existing={match.videos.filter((v) => v.role === "main" && !v.duplicate_of).map((v) => v.filename)}
              onUploaded={() => void qc.invalidateQueries({ queryKey: key })}
              shirts={
                match.opponent && !match.opponent_colors?.color ? (
                  <div className="max-w-[60ch] border-l-4 border-attn pl-3" data-testid="upload-ask-colour">
                    <p className="m-0 text-[15px]">{ta("colourTip", { opponent: oppName(match) })}</p>
                    <AskColour orgId={orgId} matchId={match.id} opponent={oppName(match)} />
                  </div>
                ) : null
              }
            />
          </section>
        )}
        <PartsPanel orgId={orgId} match={match} jobs={jobs} staff={staff} canDelete={canDelete} onChanged={() => void qc.invalidateQueries({ queryKey: key })} />
        {/* a further file (the second half, another camera): right in the Video tab, not only
            in the workbench (Q-VIDEO-PARTS) */}
        {main && staff && match.source !== "paper_report" && (
          <details id="upload" className="group" open={addOpen} onToggle={(e) => setAddOpen(e.currentTarget.open)} data-testid="add-file">
            <summary className="flex min-h-11 cursor-pointer list-none items-center gap-1.5 text-[17px] font-bold text-ink underline decoration-[1.5px] underline-offset-4 [&::-webkit-details-marker]:hidden">
              <Plus aria-hidden className="size-4" />
              {t("upload.addCamera")}
            </summary>
            <div className="pt-3">
              <UploadPanel orgId={orgId} matchId={match.id} hasMain stuck={stuckUploads} progressFiles={progress?.files ?? []} existing={match.videos.filter((v) => v.role === "main" && !v.duplicate_of).map((v) => v.filename)} onUploaded={() => void qc.invalidateQueries({ queryKey: key })} />
            </div>
          </details>
        )}
        {main && staff && parts.length === 1 && !adding && <p className="m-0 max-w-[60ch] text-[15px] text-ink-2">{tParts("later")}</p>}
        {!main && match.videos.map((v) => v.quality_report && <QualityReport key={v.id} video={v} />)}
      </div>

      {view === "game" && (
        <div className="animate-fade space-y-10">
          {/* before the match: the opponent's facts and «Spieltag starten»; the video comes after (UX test N16) */}
          {upcoming && match.opponent && (
            <section className={cn("grid gap-8", MATCHDAY_OFFERED && "md:grid-cols-[minmax(0,1fr)_340px]")} data-testid="before-match">
              {MATCHDAY_OFFERED && <div className="space-y-3">
                <h2 className="text-[26px]">{ta("beforeTitle")}</h2>
                <p className="m-0 max-w-[60ch] text-[17px]">{ta("beforeText")}</p>
                {staff && (
                  <Link href={`${base}/matchday`} className={buttonClass(matchDay ? "primary" : "secondary")} data-testid="before-matchday">
                    <Radio aria-hidden />
                    {t("live.open")}
                  </Link>
                )}
              </div>}
              <NextOpponent orgId={orgId} teamId={match.team_id} next={{ id: match.id, kickoff_at: match.kickoff_at, opponent_name: oppName(match), is_home: match.is_home } as Schemas["MatchSummary"]} played={(teamMatches.data ?? []).filter((m) => m.score_own != null)} />
            </section>
          )}
          {/* without video: first what works today, the Spielkarte and the Kurzbericht (R39) */}
          {today && <TodayBlock onPicture={cardPicture} report={telegram} />}
          {/* a match without video: the report's facts below, the way to the video on top */}
          {/* the example match is looked at, nothing to upload or file there (R1) */}
          {!main && staff && !example && Date.parse(match.kickoff_at) <= Date.now() && (
            <section className="space-y-3 border-2 border-dashed border-ink/40 p-4 md:p-6" data-testid="no-video">
              <h2 className="text-[26px]">{ta("noVideoTitle")}</h2>
              <p className="m-0 max-w-[60ch] text-[17px]">{ta("noVideoBlock")}</p>
              <Button onClick={() => setView("video")}>{ta("chooseVideo")}</Button>
            </section>
          )}
          {/* right after the analysis, no goal in the video yet: one sentence and the next step,
              not an empty tab (real-video test, second round) */}
          {staff && graphics.data?.analysis === "ready" && !graphics.data.goals.some((x) => x.has_video) && graphics.data.checks.length > 0 && (
            <section className="max-w-[60ch] space-y-3 border-l-4 border-attn pl-4" data-testid="game-next-step">
              <p className="m-0 text-[19px] font-bold">{ta("nextStepChecks", {
                  n: graphics.data.checks.length,
                  // the sentence needs both numbers: without minutes it showed its key (staging, 17.11.)
                  minutes: checkMinutes(
                    graphics.data.checks.filter((c) => c.kind === "goal").length,
                    graphics.data.checks.filter((c) => c.kind !== "goal").length,
                  ),
                })}</p>
              <Link href={`${base}/check`} className={buttonClass("primary")} data-testid="game-step">
                {ta("answerChecks", { n: graphics.data.checks.length })}
              </Link>
            </section>
          )}
          {/* analysed, every question answered, no goal found and no result: the reason and the
              next step right here, not only in the tab Video (L6) */}
          {noGoals && (
            <section className="max-w-[62ch] space-y-3 border-l-4 border-attn pl-4" data-testid="game-no-goals">
              <h2 className="text-[26px]">{t("progress.noGoalsTitle")}</h2>
              <p className="m-0 text-[17px]">{t("progress.noGoalsWhy")}</p>
              {staff && (
                <div className="flex flex-wrap gap-3">
                  <Button onClick={() => setDialog("edit")}>{t("progress.noGoalsScore")}</Button>
                  <Button variant="secondary" onClick={() => (setView("video"), setBench(true))}>
                    {t("progress.noGoalsMark")}
                  </Button>
                </div>
              )}
            </section>
          )}
          {graphics.data && (goalRuns(graphics.data).length > 0 || graphics.data.goals.some((x) => x.has_video)) && (
            <ThreeThingsView orgId={orgId} matchId={match.id} graphics={graphics.data} oppName={oppName(match)} onScenes={main ? (_, n) => setView("video", n) : undefined} onScene={main ? (id) => setView("video", null, id) : undefined} />
          )}
          <GameActions
            collect={staff && counted && hasScenes && match.opponent ? <FromMatchButton orgId={orgId} teamId={match.team_id} matchId={match.id} opponent={oppName(match)} /> : null}
            // before the match there is nothing to share yet (UX test A05), nor before a goal is
            // known (open questions alone make no reel, L6)
            // highlights are made of scenes: without a goal in the video there is none (R34)
            onHighlights={upcoming || noGoals || !hasScenes || !hasReels ? undefined : () => {
              if (more.current) more.current.open = true;
              requestAnimationFrame(() => document.getElementById("highlights")?.scrollIntoView({ behavior: "smooth", block: "start" }));
            }}
            // the Spielkarte, rendered on the server: into the chat by the share sheet, else saved (K20)
            onPicture={today ? undefined : cardPicture}
          />
          {/* without video the left column (Punkt 1, Kurzbericht) moved up: one column here */}
          <div className={cn("grid gap-12", !today && "lg:grid-cols-[minmax(0,1fr)_340px]")}>
            {!today && (
              <div className="min-w-0 space-y-10">
                {graphics.data && <PointOpen orgId={orgId} matchId={match.id} graphics={graphics.data} oppName={oppName(match)} />}
                {telegram}
              </div>
            )}
            {/* the goals by position stand once, in Zahlen (app review UX-08: no doubles) */}
            <div className="space-y-10">
              {stats.data && <ThreeFigures stats={stats.data} names={names} roster={rosterRows} />}
            </div>
          </div>
          {/* everything else of the match, as before, one step away (UX test B08); not before the
              match, when there is nothing in it yet (UX test A05) */}
          {!upcoming && (
          <details ref={more} className="group border-t-2 border-ink pt-4" data-testid="game-more">
            <summary className="fold items-baseline gap-3">
              <span className="font-slant text-[22px]">{ta("moreGame")}</span>
              <span className="text-[15px] text-ink-2 group-open:hidden">{ta("moreGameHint")}</span>
            </summary>
            <div className="mt-8 space-y-10">
          {/* only what the data carries and what is in scope (UX test B08): the course of the
              match; the comparison sits in Zahlen, the three things above, possession and attacks
              estimated from the video are not shown */}
          {stats.data && stats.data.quality.events > 0 && <OverviewView orgId={orgId} match={match} teamName={own} stats={stats.data} names={names} staff={staff} onPlay={main ? onPlay : undefined} parts={["timeline"]} span={courseSpan?.span ?? null} videoTime={courseSpan?.video ?? false} />}
          <div className="space-y-8">
            <div id="highlights" className="scroll-mt-24"><HighlightsView orgId={orgId} matchId={match.id} teamId={match.team_id} staff={staff} names={names} scenes={Boolean(main && graphics.data?.goals.some((g) => g.has_video))} /></div>
            {/* the players' personal scenes are the staff's overview (K18) */}
            {/* the players' scenes need a video: without one «Szenen neu erstellen» made nothing (review R34) */}
            {staff && <MarksPanel orgId={orgId} matchId={match.id} onPlay={main ? onPlay : undefined} />}
          </div>
            </div>
          </details>
          )}
          {!example && <AttachmentsPanel orgId={orgId} matchId={match.id} staff={staff} hasReport={graphics.data?.has_report ?? false} linked={Boolean(official.data?.official_team_id) && Boolean(match.official_game) && !scouting} />}
        </div>
      )}

      {view === "numbers" && (
        <div className="animate-fade">
          <NumbersView stats={stats.data ?? null} graphics={graphics.data ?? null} roster={rosterRows} orgId={orgId} match={match} names={names} onPlay={main ? onPlay : undefined}>
          {stats.data && stats.data.quality.events > 0 && (
            <section id="numbers-overview" className="scroll-mt-24">
              <OverviewView orgId={orgId} match={match} teamName={own} stats={stats.data} names={names} staff={staff} onPlay={main ? onPlay : undefined} videoNote={videoNote} parts={["basis", "decided", "comparison"]} />
            </section>
          )}
          {numberParts.length === 0 && (
            // why there are no figures and the way to them (L6)
            <EmptyState icon={<ChartNoAxesColumn />} title={noGoals ? t("progress.noGoalsTitle") : progressShown ? t("progress.numbersRunning") : t("stats.noData")}>
              <span className="block" data-testid="numbers-empty">
                {noGoals ? t("progress.noGoalsWhy") : progressShown ? t("progress.numbersRunningText") : staff && match.source !== "paper_report" ? t(main ? "progress.numbersNoEvents" : "stats.noDataHint") : null}
              </span>
              {staff && noGoals && (
                <span className="mt-3 flex flex-wrap justify-center gap-3">
                  <Button size="sm" onClick={() => setDialog("edit")}>{t("progress.noGoalsScore")}</Button>
                  <Button size="sm" variant="secondary" onClick={() => (setView("video"), setBench(true))}>
                    {t("progress.noGoalsMark")}
                  </Button>
                </span>
              )}
              {staff && !main && !progressShown && match.source !== "paper_report" && (
                <span className="mt-3 flex justify-center">
                  <Button size="sm" onClick={toUpload}>{t("upload.title")}</Button>
                </span>
              )}
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
                  teamName={own}
                  oppName={oppName(match)}
                  videoNote={videoNote}
                  short={covers != null && covers.reduce((s, c) => s + c.to - c.from, 0) < match.period_s}
                />
              ) : stats.data ? (
                (() => {
                  const props = { orgId, match, teamName: own, stats: stats.data, names, staff, onPlay: main ? onPlay : undefined };
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
        <MatchAdmin orgId={orgId} match={match} sides={sides} onSaved={() => setDialog(null)} />
      </Dialog>
      <Dialog open={dialog === "exchange"} onOpenChange={(o) => setDialog(o ? "exchange" : null)} title={t("exchange.title")}>
        <ExchangePanel orgId={orgId} matchId={match.id} canImport={staff} />
      </Dialog>
    </div>
    </MatchSidesProvider>
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
      <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 text-sm [&::-webkit-details-marker]:hidden">
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

function MatchAdmin({ orgId, match, sides, onSaved }: { orgId: string; match: Match; sides: MatchSides; onSaved: () => void }) {
  const t = useTranslations();
  // the analysed video: the colours show who the analysis sees in them
  const main = timelineVideo(match.videos);
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
      {/* the home team first, as in the head (BUG-18); the result of the whole match, not the
          goals in the video (BUG-05) */}
      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="mb-2 text-sm font-semibold">{t("matches.score")}</legend>
        {homeFirst(
          sides,
          <Input key="own" label={sides.own} name="score_own" type="number" min={0} max={99} defaultValue={match.score_own ?? ""} />,
          <Input key="opp" label={sides.opp} name="score_opponent" type="number" min={0} max={99} defaultValue={match.score_opponent ?? ""} />,
        )}
        <p className="col-span-2 m-0 text-[15px] text-ink-2">{t("matches.scoreFinalHint")}</p>
      </fieldset>
      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="mb-2 text-sm font-semibold">{t("matches.halftime")}</legend>
        {homeFirst(
          sides,
          <Input key="own" label={sides.own} name="ht_own" type="number" min={0} max={99} defaultValue={match.halftime_own ?? ""} />,
          <Input key="opp" label={sides.opp} name="ht_opp" type="number" min={0} max={99} defaultValue={match.halftime_opponent ?? ""} />,
        )}
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
        <KitFields kits={kits} onChange={setKits} names={sides.neutral ? { own: sides.own, opp: sides.opp } : null} pictures={main ? { orgId, videoId: main.id } : null} />
      </fieldset>
      <Button type="submit">{t("common.save")}</Button>
    </form>
  );
}

/** The two teams as rows of a scoreboard: name left, goals right, our row in full strength. */
// a share above 100 % means the sources disagree (e.g. goals from a report, attacks from a clip)

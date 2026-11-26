"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Crosshair, Keyboard, Maximize2, Share2, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, type FormEvent, type Ref } from "react";
import { useRouter } from "next/navigation";
import { Tagger } from "@/components/analysis/tagger";
import { useMatchRoster } from "@/components/domain/match-sides";
import { FROM_VIDEO_KEY, playFromVideo } from "@/lib/play-from-video";
import { Button } from "@/components/ui/button";
import { ShareButton } from "@/components/sharing/share-button";
import { Alert } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { control, Input, Select } from "@/components/ui/field";
import { SpotlightControls, useSpotlight } from "@/components/video/spotlight-controls";
import { SpotlightOverlay } from "@/components/video/spotlight";
import { geometryOf } from "@/lib/moving-camera";
import { MultiAngleControls, useMultiAngle } from "@/components/video/multi-angle";
import { SyncedCam } from "@/components/video/synced-cam";
import { cameraAt } from "@/lib/best-camera";
import { DrawLayer } from "@/components/video/draw-layer";
import { VideoPlayer, type Marker, type PlayerHandle } from "@/components/video/player";
import type { Shape, Tool } from "@/components/video/shapes";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { courtUnconfirmed, coverage, firstOpen, steps } from "@/lib/match-workflow";
import { goalRows } from "@/lib/official-goals";
import { cn } from "@/lib/utils";
import { AnalysisPanel } from "./analysis-panel";
import { CameraSwitch } from "./camera-switch";
import { FormationsCard } from "./formations-card";
import { IdentityPanel, ownTracks } from "./identity-panel";
import { useWorkspaceData } from "./use-workspace-data";
import { GoalCandidatesPanel } from "./goal-candidates";
import { ShotCandidatesPanel } from "./shot-candidates";
import { KickoffPanel } from "./kickoff-panel";
import { MatchTimeline } from "./match-timeline";
import { OfficialGoalsPanel } from "./official-goals";
import { OfficialReportImport } from "./official-report";
import { WorkRail, type Pane } from "./work-rail";
import { usePartMarkers } from "./parts-panel";
import { useGameTime } from "./game-time";
import { TeamFeedView } from "./feed-views";

type Match = Schemas["MatchOut"];
type Video = Schemas["VideoOut"];
type Tab = "comments" | "clips" | "drawings";
const TOOLS: Tool[] = ["arrow", "line", "circle", "freehand", "spotlight"];
const COLORS = ["#facc15", "#ef4444", "#22c55e", "#3b82f6", "#ffffff"];

export function Workspace({
  orgId,
  match,
  video,
  staff,
  teamName,
  oppName,
  names,
  setup,
  requestPane = null,
  requestDraw = null,
  handle,
  checkSteps = true,
}: {
  orgId: string;
  match: Match;
  video: Video;
  staff: boolean;
  teamName: string;
  oppName: string;
  names: Record<string, string>;
  /** the video's own setup (more cameras, quality): shown with the court, not under every step */
  setup?: React.ReactNode;
  /** a pane to open from outside; a new object each time */
  requestPane?: { pane: Pane } | null;
  /** drawing asked for from outside (the stage's «Zeichnen»): at this moment; a new object each time */
  requestDraw?: { t_ms: number } | null;
  handle?: Ref<PlayerHandle | null>;
  /** the work steps (court, throw-off, goals, persons) in the rail; off where Prüfen asks them */
  checkSteps?: boolean;
}) {
  const t = useTranslations();
  const qc = useQueryClient();
  const router = useRouter();
  const raw = useRef<PlayerHandle>(null);
  // camera switch (M5): every time in this component is main-video time; other cameras are shifted
  // by their sync offset (time in that video = main time + offset)
  // the match video (its first part plays all parts) and the other cameras; the further parts of
  // the match are not cameras of their own (Echtlauf 5: «Hauptkamera | Hauptkamera»)
  const cams = match.videos.filter((v) => v.status === "ready" && v.has_hls && (v.id === video.id || v.role !== "main" || v.part == null));
  const [camId, setCamId] = useState(video.id);
  const cam = cams.find((c) => c.id === camId) ?? video;
  const offset = cam.id === video.id ? 0 : cam.time_offset_ms;
  const off = useRef(offset);
  off.current = offset;
  const player = useRef<PlayerHandle>({
    seek: (ms: number) => raw.current?.seek(Math.max(0, ms + off.current)),
    play: () => raw.current?.play(),
    pause: () => raw.current?.pause(),
    time: () => (raw.current?.time() ?? 0) - off.current,
    video: () => raw.current?.video() ?? null,
  });
  useImperativeHandle(handle, () => player.current, []);
  const pendingSeek = useRef<number | null>(null);
  function switchCamera(id: string) {
    pendingSeek.current = player.current.time();
    const wasPlaying = raw.current?.video()?.paused === false;
    setCamId(id);
    // seek once the new source has its metadata
    window.setTimeout(() => {
      const v = raw.current?.video();
      if (!v) return;
      const go = () => {
        if (pendingSeek.current != null) player.current.seek(pendingSeek.current);
        pendingSeek.current = null;
        if (wasPlaying) player.current.play();
      };
      if (v.readyState >= 1) go();
      else v.addEventListener("loadedmetadata", go, { once: true });
    }, 0);
  }
  const [now, setNow] = useState(0);
  const [tab, setTab] = useState<Tab>("comments");
  const [pane, setPane] = useState<Pane | null>(null);
  const [goalList, setGoalList] = useState<"candidates" | "report" | null>(null);
  // review mode: the workspace full screen, one goal candidate after the other
  const [reviewing, setReviewing] = useState(false);
  // what the full-screen review goes through: goal candidates or shot moments
  const [reviewKind, setReviewKind] = useState<"goals" | "shots">("goals");
  const [activeCandidate, setActiveCandidate] = useState<string | null>(null);
  const [activeShot, setActiveShot] = useState<string | null>(null);
  useEffect(() => {
    if (!reviewing) return;
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && (e.preventDefault(), setReviewing(false));
    window.addEventListener("keydown", onEsc);
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onEsc);
      document.body.style.overflow = before;
    };
  }, [reviewing]);
  const [drawing, setDrawing] = useState(false);
  const [tool, setTool] = useState<Tool>("arrow");
  const [color, setColor] = useState(COLORS[0]!);
  const [shapes, setShapes] = useState<Shape[]>([]);
  const [markIn, setMarkIn] = useState<number | null>(null);
  const [markOut, setMarkOut] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<ErrorKey | null>(null);
  const m = { org_id: orgId, match_id: match.id };
  const media = `/v1/orgs/${orgId}/videos/${cam.id}/media`;

  const multi = useMultiAngle(cams, video.id);
  const pickCam = multi.pick;
  const { comments, clips, analysis, annotations, playlists, events, hasReport, candidates, shotCandidates, official } = useWorkspaceData({
    orgId,
    match,
    videoId: video.id,
    staff,
    autoCamera: multi.auto && cams.length > 1,
  });
  const kitColours = useMemo(
    () => ({ home: match.kit_own, home_gk: match.kit_own_gk, away: match.kit_opponent, away_gk: match.kit_opponent_gk, referee: match.kit_referee ?? "#111827" }),
    [match],
  );
  const getTime = useCallback(() => player.current.time() ?? 0, []);
  // the clock in the comment box needs only a few updates per second, not every video frame
  const lastTick = useRef(0);
  const onTime = useCallback((camMs: number) => {
    const ms = camMs - off.current;
    const now = performance.now();
    if (now - lastTick.current > 250) {
      lastTick.current = now;
      setNow(ms);
    }
  }, []);

  const partMarkers = usePartMarkers(match.videos);
  const markers: Marker[] = useMemo(
    () => [
      // where the second half (a further file of the match) starts
      ...partMarkers,
      ...(comments.data ?? []).map((c) => ({ t_ms: c.t_ms, kind: "comment" as const, label: c.body })),
      ...(clips.data ?? []).map((c) => ({ t_ms: c.start_ms, kind: "clip" as const, label: c.title ?? "" })),
      ...(annotations.data ?? []).map((a) => ({ t_ms: a.t_ms, kind: "drawing" as const })),
    ],
    [comments.data, clips.data, annotations.data, partMarkers],
  );

  const addComment = useMutation({
    mutationFn: async (body: string) =>
      api.POST("/v1/orgs/{org_id}/matches/{match_id}/comments", { params: { path: m }, body: { t_ms: Math.round(now), body } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["comments", match.id] }),
  });
  const deleteComment = useMutation({
    mutationFn: async (id: string) => api.DELETE("/v1/orgs/{org_id}/comments/{comment_id}", { params: { path: { org_id: orgId, comment_id: id } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["comments", match.id] }),
  });

  const startDrawing = useCallback(() => {
    player.current.pause();
    setDrawing(true);
    setPane("notes");
    setTab("drawings");
  }, []);

  async function saveDrawing() {
    if (shapes.length === 0) return;
    const { error } = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/annotations", {
      params: { path: m },
      body: { t_ms: Math.round(player.current.time() ?? now), duration_ms: 4000, shapes: shapes.map((s) => ({ ...s, text: s.text ?? null })) },
    });
    if (error) return setFailure(errorKey(error));
    setFailure(null);
    setShapes([]);
    setDrawing(false);
    setNotice(t("draw.saved"));
    void qc.invalidateQueries({ queryKey: ["annotations", match.id] });
  }

  async function saveClip(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (markIn == null || markOut == null || markOut <= markIn) return;
    const form = e.currentTarget; // React clears currentTarget after the first await
    const f = new FormData(form);
    const title = String(f.get("title") ?? "").trim() || null;
    const playlistId = String(f.get("playlist") ?? "");
    const clip = { match_id: match.id, start_ms: Math.round(markIn), end_ms: Math.round(markOut), title };
    const { error } = playlistId
      ? await api.POST("/v1/orgs/{org_id}/playlists/{playlist_id}/items", {
          params: { path: { org_id: orgId, playlist_id: playlistId } },
          body: { clip },
        })
      : await api.POST("/v1/orgs/{org_id}/clips", { params: { path: { org_id: orgId } }, body: clip });
    if (error) return setFailure(errorKey(error));
    setFailure(null);
    if (playlistId) void qc.invalidateQueries({ queryKey: ["playlists", match.team_id] });
    setMarkIn(null);
    setMarkOut(null);
    form.reset();
    setNotice(t("clips.saved"));
    void qc.invalidateQueries({ queryKey: ["clips", match.id] });
  }

  const paneId = `ws-${match.id}`;
  const spot = useSpotlight(analysis.data ?? null);
  const spotGeometry = geometryOf(analysis.data, `/v1/orgs/${orgId}/videos/${video.id}`);
  const [spotOpen, setSpotOpen] = useState(false);
  const spotShown = spotOpen || spot.track != null || spot.picking;
  const mainVideo = useCallback(() => raw.current?.video() ?? null, []);
  // best camera around events (4.5): the goal camera takes over shortly before a shot on goal
  const [autoCamId, setAutoCamId] = useState<string | null>(null);
  useEffect(() => {
    if (!multi.auto) return setAutoCamId(null);
    const id = window.setInterval(() => {
      const best = cameraAt(player.current.time() ?? 0, events.data ?? [], cams);
      setAutoCamId(best);
      if (best) pickCam(best);
    }, 250);
    return () => window.clearInterval(id);
  }, [multi.auto, events.data, cams, pickCam]);
  const autoCam = multi.auto && autoCamId !== null;
  // our roster only in a match of the team; an observed match goes by shirt numbers (L4)
  const roster = useMatchRoster(orgId, match);
  const spotNames = Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, `#${r.jersey_number ?? "?"} ${r.first_name}`]));
  const spotLabel = (() => {
    const tr = analysis.data?.tracks.find((x) => x.track_no === spot.track);
    return tr ? (tr.player_id && spotNames[tr.player_id]) || (tr.number != null ? `#${tr.number}` : "") : "";
  })();

  // the order of work: court, throw-off, goals, players
  const durationMs = video.duration_s ? video.duration_s * 1000 : null;
  const rate = candidates.data?.default_rate ?? 2;
  const a = analysis.data;
  const spansFor = coverage(match.kickoff_ms, match.period_s, video.duration_s ? video.duration_s * 1000 : null);
  const reportOpen = hasReport && official.data?.imported ? goalRows(official.data, "open", false, spansFor).length : null;
  const stepList = steps({
    analysis: a
      ? { status: a.status, needsCalibration: a.needs_calibration === true, unconfirmed: courtUnconfirmed(a) }
      : null,
    kickoff: match.kickoff_ms,
    periodS: match.period_s,
    durationMs,
    candidatesOpen: candidates.data && candidates.data.counts.total > 0 ? (candidates.data.counts.open_by_rate[String(rate)] ?? 0) : null,
    // only goals the video can show: one beyond the clip is not open
    officialOpen: reportOpen,
    unassigned: a?.status === "ready" && a.tracks.length > 0 ? ownTracks(a.tracks).filter((tr) => !tr.player_id).length : null,
  });
  const loaded = !analysis.isLoading && !candidates.isLoading && !(hasReport && official.isLoading);
  // players watch and comment; the court, defence systems and events are the coach's workbench
  // shots to review sit next to the events they become
  const hasShots = (shotCandidates.data?.counts.total ?? 0) > 0;
  const tools: Pane[] = staff
    ? ["events", ...(hasShots ? (["shots"] as const) : []), ...(a?.status === "ready" ? (["formations"] as const) : []), "notes", "feedback"]
    : ["notes"];
  // another tab asks for a pane (e.g. "Feedback geben" from the scenes tab)
  useEffect(() => {
    if (requestPane) setPane(requestPane.pane);
  }, [requestPane]);
  // «Zeichnen» on the stage (app review BUG-13): the moment of the stage, paused, the drawing tools
  // open beside it, the player in view; once its picture can be sought
  const drawBox = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!requestDraw || !staff) return;
    const id = window.setInterval(() => {
      const v = player.current.video();
      if (!v || v.readyState < 1) return;
      window.clearInterval(id);
      player.current.seek(requestDraw.t_ms);
      startDrawing();
      const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      drawBox.current?.scrollIntoView({ block: "start", behavior: still ? "auto" : "smooth" });
    }, 200);
    const stop = window.setTimeout(() => window.clearInterval(id), 30_000);
    return () => (window.clearInterval(id), window.clearTimeout(stop));
  }, [requestDraw, staff, startDrawing]);
  const [setupOpen, setSetupOpen] = useState(false);
  const chosen: Pane = pane ?? (staff && (checkSteps || setupOpen) ? (firstOpen(stepList) ?? "notes") : staff ? "events" : "notes");
  // the first open step is shown once the lists are in; from then on the coach decides
  useEffect(() => {
    if (pane == null && loaded) setPane(chosen);
  }, [loaded]); // eslint-disable-line react-hooks/exhaustive-deps
  const { at: gameAt } = useGameTime(match.kickoff_ms, match.period_s);
  // the clock on the picture follows the player: client only, so the server HTML stays the same
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const jump = useCallback((ms: number) => {
    player.current.seek(ms);
    player.current.play();
  }, []);
  // a clip (goal candidate): plays from `from` and stops at `to`; a seek elsewhere ends it
  const clipEnd = useRef<(() => void) | null>(null);
  useEffect(() => () => clipEnd.current?.(), []);
  const playClip = useCallback((from: number, to: number) => {
    clipEnd.current?.();
    player.current.seek(from);
    player.current.play();
    const v = player.current.video();
    if (!v) return;
    let started = false; // the seek may land after the first time updates
    const tick = () => {
      const ms = player.current.time();
      if (!started) started = ms >= from - 500 && ms < to;
      else if (ms < from - 2000 || ms > to + 1500) stop(); // the coach seeked elsewhere
      else if (ms >= to) {
        v.pause();
        stop();
      }
    };
    const stop = () => {
      v.removeEventListener("timeupdate", tick);
      clipEnd.current = null;
    };
    v.addEventListener("timeupdate", tick);
    clipEnd.current = stop;
  }, []);

  const onKey = useCallback(
    (key: string) => {
      if (!staff) return false;
      const ms = player.current.time() ?? 0;
      if (key === "i") return setMarkIn(ms), setPane("notes"), setTab("clips"), true;
      if (key === "o") return setMarkOut(ms), setPane("notes"), setTab("clips"), true;
      if (key === "d") return startDrawing(), true;
      return false;
    },
    [staff, startDrawing],
  );

  const seekPaused = (ms: number) => {
    player.current.pause();
    player.current.seek(ms);
  };
  const openCandidates = candidates.data && candidates.data.counts.total > 0;
  const list = goalList ?? (openCandidates || !hasReport ? "candidates" : "report");
  const shown: Pane = reviewing ? reviewKind : chosen;
  const openNow = candidates.data?.counts.open_by_rate[String(rate)] ?? 0;
  const shotsOpen = shotCandidates.data?.counts.open_by_rate[String(shotCandidates.data.default_rate)] ?? 0;
  // Prüfen (/matches/[m]/check) opens the full-screen review at once: goals first, then shots
  const checkOpened = useRef(false);
  useEffect(() => {
    if (checkOpened.current || !staff || !candidates.data || !shotCandidates.data) return;
    if (new URLSearchParams(window.location.search).get("check") !== "1") return;
    checkOpened.current = true;
    if (openNow > 0) {
      setGoalList("candidates");
      setReviewKind("goals");
      setReviewing(true);
    } else if (shotsOpen > 0) {
      setReviewKind("shots");
      setReviewing(true);
    }
  }, [staff, candidates.data, shotCandidates.data, openNow, shotsOpen]);
  return (
    <div
      className={cn("space-y-5", reviewing && "fixed inset-0 z-[60] !m-0 h-dvh overflow-y-auto bg-background p-4 sm:p-6 lg:px-10")}
      role={reviewing ? "dialog" : undefined}
      aria-modal={reviewing || undefined}
      aria-labelledby={reviewing ? `${paneId}-review` : undefined}
    >
      {reviewing ? (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-foreground/15 pb-3">
          <h2 id={`${paneId}-review`} className="font-display text-3xl">
            {reviewKind === "shots" ? t("shotCandidates.title") : t("workflow.goals")}
          </h2>
          <span className="text-muted">{`${teamName} ${t("matches.vs")} ${oppName}`}</span>
          <span className="ml-auto font-score text-xl tabular-nums" aria-live="polite">
            {t("workflow.reviewLeft", { n: reviewKind === "shots" ? shotsOpen : openNow })}
          </span>
          <Button variant="secondary" onClick={() => setReviewing(false)} data-testid="review-close">
            <X aria-hidden />
            {t("workflow.reviewClose")}
          </Button>
        </div>
      ) : staff || tools.length > 1 ? (
        <div>
          <WorkRail steps={staff && (checkSteps || setupOpen) ? stepList : []} tools={tools} value={shown} onChange={setPane} idPrefix={paneId} />
          {/* the questions live in Prüfen (UX test B10); the setup by hand stays one tap away */}
          {staff && !checkSteps && (
            <button type="button" onClick={() => setSetupOpen((v) => !v)} aria-expanded={setupOpen} className="mt-2 min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4" data-testid="setup-toggle">
              {setupOpen ? t("workflow.setupClose") : t("workflow.setupOpen")}
            </button>
          )}
        </div>
      ) : null}
      <div ref={drawBox} className="scroll-mt-20 grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_24rem] xl:grid-cols-[minmax(0,1fr)_27rem]">
      {/* the player stays in view while the coach works through a list beside it */}
      {/* phones: the column dissolves into the grid, so the player can stay at the top while the
          list below it scrolls */}
      <div className="min-w-0 max-lg:contents lg:sticky lg:top-4 lg:space-y-3">
        <div
          className={cn(
            "relative max-lg:sticky max-lg:z-20 max-lg:self-start",
            reviewing ? "max-lg:top-0" : "max-lg:top-14",
            multi.mode === "side" && multi.secondary && !offset && "grid gap-2 md:grid-cols-2",
          )}
        >
        <VideoPlayer
          ref={raw}
          src={`${media}/hls/master.m3u8`}
          poster={cam.has_poster ? `${media}/poster.jpg` : undefined}
          thumbsVtt={cam.has_thumbnails ? `${media}/thumbs.vtt` : undefined}
          fps={cam.fps}
          markers={offset ? markers.map((mk) => ({ ...mk, t_ms: mk.t_ms + offset })) : markers}
          annotations={
            drawing || offset
              ? [] // drawings belong to the main camera picture
              : (annotations.data ?? []).map((a) => ({ ...a, shapes: a.shapes as Shape[] }))
          }
          onTime={onTime}
          onKey={onKey}
          // the controls read the match clock once the video sits on it (main camera only)
          clock={spansFor && !offset ? gameAt : undefined}
          overlay={
            drawing ? (
              <DrawLayer tool={tool} color={color} shapes={shapes} onChange={setShapes} />
            ) : spot.ready && spotGeometry && !offset ? (
              <SpotlightOverlay
                baseUrl={`/v1/orgs/${orgId}/videos/${video.id}/tracks`}
                chunkMs={analysis.data!.chunk_ms!}
                geometry={spotGeometry}
                track={spot.track}
                label={spotLabel}
                getTime={getTime}
                dim={spot.dim}
                showTrail={spot.trail}
                picking={spot.picking}
                onPick={(n) => spot.set({ track: n, picking: false })}
              />
            ) : undefined
          }
        />
        {/* the match clock on the picture, as on a broadcast: what the coach talks about */}
        {mounted && spansFor && !drawing && (
          <span aria-hidden className="pointer-events-none absolute left-2 top-2 z-10 bg-black/65 px-2 py-0.5 font-score text-base text-white tabular-nums">
            {gameAt(now)}
          </span>
        )}
        {multi.secondaryCam && !offset && (multi.mode !== "single" || autoCam) && (
          <SyncedCam
            key={multi.secondaryCam.id}
            src={`/v1/orgs/${orgId}/videos/${multi.secondaryCam.id}/media/hls/master.m3u8`}
            offsetMs={multi.secondaryCam.time_offset_ms}
            main={mainVideo}
            label={t(`camera.${multi.secondaryCam.role}` as "camera.main")}
            className={cn(
              "bg-black",
              multi.mode === "side"
                ? "aspect-video w-full"
                : autoCam && multi.mode === "single"
                  ? "pointer-events-none absolute inset-0 size-full object-contain"
                  : "pointer-events-none absolute right-2 top-2 w-1/3 border-2 border-white",
            )}
          />
        )}
        </div>
        {cams.length > 1 && !offset && <MultiAngleControls cams={cams} state={multi} />}
        {cams.length > 1 && <CameraSwitch orgId={orgId} cams={cams} active={cam} staff={staff} onSwitch={switchCamera} />}
        {/* quiet tools under the picture; the spotlight unfolds on demand */}
        <div className={cn("flex flex-wrap items-center gap-1 max-lg:order-last", reviewing && "hidden")}>
          {spot.ready && !offset && (
            <Button variant={spotShown ? "secondary" : "quiet"} size="sm" aria-expanded={spotShown} aria-controls={`${paneId}-spot`} onClick={() => setSpotOpen((v) => !v)}>
              <Crosshair aria-hidden />
              {t("spotlight.title")}
            </Button>
          )}
          {staff && analysis.data?.status === "ready" && analysis.data.chunk_ms && (analysis.data.chunks ?? 0) > 0 && (
            <Button
              variant="quiet"
              size="sm"
              title={t("tactics.fromVideoHint")}
              onClick={async () => {
                player.current.pause();
                const ms = Math.round(player.current.time());
                const doc = await playFromVideo(`/v1/orgs/${orgId}/videos/${video.id}/tracks`, analysis.data!.chunk_ms!, ms, analysis.data!.tracks);
                if (!doc) return setFailure("generic");
                try {
                  window.sessionStorage.setItem(FROM_VIDEO_KEY, JSON.stringify({ doc, match_id: match.id, t_ms: ms }));
                } catch {
                  return setFailure("generic");
                }
                router.push(`/app/${orgId}/teams/${match.team_id}/plays/new?from=video`);
              }}
            >
              {t("tactics.fromVideo")}
            </Button>
          )}
          {/* keys teach only where there is a keyboard */}
          <details className="group relative pointer-coarse:hidden">
            <summary className="inline-flex min-h-8 cursor-pointer list-none items-center gap-1.5 px-3 text-[0.9375rem] font-medium text-muted hover:bg-surface hover:text-foreground [&::-webkit-details-marker]:hidden">
              <Keyboard aria-hidden className="size-4" />
              {t("player.shortcuts")}
            </summary>
            <p className="absolute left-0 z-20 mt-1 w-80 max-w-[85vw] bg-raised p-3 text-xs leading-relaxed text-muted ring-1 ring-border">{t("player.shortcutsList")}</p>
          </details>
        </div>
        {spot.ready && !offset && !reviewing && spotShown && (
          <div id={`${paneId}-spot`} className="max-lg:order-last">
            <SpotlightControls spot={spot} tracks={analysis.data!.tracks} names={spotNames} />
          </div>
        )}
        <div className="max-lg:order-last">
        <MatchTimeline
          spans={spansFor}
          periodS={match.period_s}
          kickoff={match.kickoff_ms}
          nowMs={now}
          official={hasReport ? official.data : null}
          // while shots are reviewed, their moments take the candidate lane
          candidates={staff ? (shown === "shots" ? shotCandidates.data : candidates.data) : null}
          candidatesLabel={shown === "shots" ? "laneShots" : "laneCandidates"}
          rate={shown === "shots" ? (shotCandidates.data?.default_rate ?? 4) : rate}
          activeId={shown === "goals" ? activeCandidate : shown === "shots" ? activeShot : null}
          ownName={teamName}
          oppName={oppName}
          events={staff ? events.data : null}
          notes={[...(comments.data ?? []).map((c) => c.t_ms), ...(clips.data ?? []).map((c) => c.start_ms), ...(annotations.data ?? []).map((x) => x.t_ms)]}
          onSetKickoff={staff ? () => (setSetupOpen(true), setPane("kickoff")) : undefined}
        />
        </div>
        {failure && <Alert className="py-2">{t(`errors.${failure}`)}</Alert>}
        {notice && (
          <Alert kind="success" className="py-2">
            {notice}
          </Alert>
        )}
      </div>

      <div
        id={`${paneId}-pane`}
        // a tab panel only when there is a tab row (players see the one tool without tabs)
        role={reviewing || !(staff || tools.length > 1) ? undefined : "tabpanel"}
        aria-labelledby={reviewing || !(staff || tools.length > 1) ? undefined : `${paneId}-tab-${shown}`}
        className="flex min-w-0 flex-col gap-4 lg:sticky lg:top-4 lg:max-h-[calc(100dvh-2rem)] lg:overflow-y-auto lg:pr-1"
      >
        {shown === "court" && (
          <>
            <AnalysisPanel
              analysis={a ?? null}
              orgId={orgId}
              videoId={video.id}
              colours={kitColours}
              getTime={getTime}
              canCalibrate={staff}
              // the court is checked: on to the next open step
              onConfirmed={() => setPane(null)}
            />
            {setup && <div className="space-y-3 border-t border-foreground/15 pt-4">{setup}</div>}
          </>
        )}
        {shown === "kickoff" && staff && (
          <KickoffPanel orgId={orgId} matchId={match.id} kickoff={match.kickoff_ms} periodS={match.period_s} durationMs={durationMs} getTime={getTime} onSeek={seekPaused} />
        )}
        {shown === "goals" && staff && (
          <div className="flex min-h-0 flex-1 flex-col gap-4">
            {hasReport && openCandidates && !reviewing && (
              <Segmented<"candidates" | "report">
                className="border-b border-foreground/15 max-lg:order-last"
                label={t("workflow.goalLists")}
                variant="underline"
                size="sm"
                value={list}
                onChange={setGoalList}
                items={[
                  { value: "candidates", label: t("workflow.listCandidates", { n: openNow }) },
                  { value: "report", label: t("workflow.listReport", { n: reportOpen ?? 0 }) },
                ]}
              />
            )}
            {list === "candidates" && openCandidates && !reviewing && openNow > 0 && (
              <Button variant="secondary" className="self-start max-lg:order-last" onClick={() => (setGoalList("candidates"), setReviewKind("goals"), setReviewing(true))} data-testid="review-open">
                <Maximize2 aria-hidden />
                {t("workflow.reviewOpen")}
              </Button>
            )}
            {list === "report" && hasReport && !reviewing ? (
              <OfficialGoalsPanel orgId={orgId} matchId={match.id} ownName={teamName} oppName={oppName} isHome={match.is_home} names={names} covers={spansFor} onPlay={jump} />
            ) : openCandidates ? (
              <GoalCandidatesPanel orgId={orgId} matchId={match.id} ownName={teamName} oppName={oppName} onClip={playClip} onActive={setActiveCandidate} focusMode={reviewing} />
            ) : (
              <p className="text-sm text-muted">{t("workflow.goalsNone")}</p>
            )}
            {!hasReport && (
              <div className="space-y-1">
                <p className="text-sm text-muted">{t("workflow.noReport")}</p>
                <OfficialReportImport orgId={orgId} matchId={match.id} />
              </div>
            )}
          </div>
        )}
        {shown === "players" && staff && a?.status === "ready" && (
          <IdentityPanel orgId={orgId} match={match} videoId={video.id} tracks={a.tracks} onSeek={seekPaused} at={gameAt} />
        )}
        {shown === "players" && staff && a?.status !== "ready" && <p className="text-sm text-muted">{t("workflow.players_waiting")}</p>}
        {shown === "events" && staff && (
          <div className="flex min-h-0 flex-1 flex-col">
            <Tagger orgId={orgId} match={match} teamName={teamName} getTime={getTime} />
          </div>
        )}
        {shown === "shots" && staff && (
          <div className="flex min-h-0 flex-1 flex-col gap-4">
            {!reviewing && shotsOpen > 0 && (
              <Button variant="secondary" className="self-start max-lg:order-last" onClick={() => (setReviewKind("shots"), setReviewing(true))} data-testid="shots-review-open">
                <Maximize2 aria-hidden />
                {t("workflow.reviewOpen")}
              </Button>
            )}
            <ShotCandidatesPanel
              orgId={orgId}
              matchId={match.id}
              ownName={teamName}
              oppName={oppName}
              names={names}
              onClip={playClip}
              onActive={setActiveShot}
              onSeek={seekPaused}
              onSetKickoff={match.kickoff_ms?.["1"] == null ? () => (setSetupOpen(true), setPane("kickoff")) : undefined}
              focusMode={reviewing}
            />
          </div>
        )}
        {shown === "formations" && a?.status === "ready" && <FormationsCard formations={a.formations ?? []} onSeek={jump} />}
        {shown === "feedback" && staff && (
          // beside the player: watch a scene and write the note without leaving the list
          <TeamFeedView orgId={orgId} matchId={match.id} onPlay={jump} kickoff={match.kickoff_ms} periodS={match.period_s} compact />
        )}
        {shown === "notes" && (
          <div className="flex min-h-0 flex-1 flex-col gap-4">
        <Segmented<Tab>
          label={t("workflow.notes")}
          size="sm"
          value={tab}
          onChange={setTab}
          items={(["comments", "clips", "drawings"] as const).map((k) => ({
            value: k,
            label: t(k === "drawings" ? "draw.list" : `${k}.title`),
          }))}
        />
        {tab === "comments" && (
          <div role="tabpanel" className="flex min-h-0 flex-1 flex-col gap-2">
            <ul className="min-h-0 flex-1 space-y-2 overflow-auto text-sm" data-testid="comments">
              {(comments.data ?? []).length === 0 && <li className="text-muted">{t("comments.emptyHint", { time: gameAt(now) })}</li>}
              {(comments.data ?? []).map((c) => (
                <li key={c.id} className="bg-surface px-3 py-2">
                  <button className="bg-accent/10 px-2 py-0.5 text-xs font-semibold text-accent tabular-nums hover:bg-accent/20" onClick={() => player.current.seek(c.t_ms)}>
                    {gameAt(c.t_ms)}
                  </button>{" "}
                  <span className="text-xs text-muted">{c.author_name}</span>
                  <p>{c.body}</p>
                  {c.can_delete && (
                    <button className="text-xs text-muted underline" onClick={() => deleteComment.mutate(c.id)}>
                      {t("comments.delete")}
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const input = e.currentTarget.elements.namedItem("body") as HTMLInputElement;
                if (input.value.trim()) addComment.mutate(input.value.trim());
                input.value = "";
              }}
              className="flex gap-2"
            >
              <label className="sr-only" htmlFor="comment-body">
                {t("comments.placeholder", { time: gameAt(now) })}
              </label>
              <input
                id="comment-body"
                name="body"
                maxLength={2000}
                placeholder={t("comments.placeholder", { time: gameAt(now) })}
                className={cn(control, "min-w-0 flex-1")}
              />
              <Button type="submit" variant="secondary">
                {t("comments.add")}
              </Button>
            </form>
          </div>
        )}

        {tab === "clips" && (
          <div role="tabpanel" className="flex min-h-0 flex-1 flex-col gap-3">
            {staff && (
              <form onSubmit={saveClip} className="space-y-2" aria-label={t("clips.save")}>
                <div className="flex gap-2">
                  <Button variant="secondary" className="flex-1" onClick={() => setMarkIn(player.current.time() ?? now)}>
                    {markIn != null ? formatClock(markIn) : t("clips.markIn")}
                  </Button>
                  <Button variant="secondary" className="flex-1" onClick={() => setMarkOut(player.current.time() ?? now)}>
                    {markOut != null ? formatClock(markOut) : t("clips.markOut")}
                  </Button>
                </div>
                <Input label={t("clips.clipTitle")} name="title" maxLength={200} />
                <Select label={t("clips.toPlaylist")} name="playlist" defaultValue="">
                  <option value="">{t("clips.noPlaylist")}</option>
                  {(playlists.data ?? []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title}
                    </option>
                  ))}
                </Select>
                <Button type="submit" disabled={markIn == null || markOut == null || markOut <= markIn}>
                  {t("clips.save")}
                </Button>
              </form>
            )}
            <ul className="min-h-0 flex-1 space-y-1 overflow-auto text-sm" data-testid="clips">
              {(clips.data ?? []).length === 0 && <li className="text-muted">{t("clips.empty")}</li>}
              {(clips.data ?? []).map((c) => (
                <li key={c.id} className="flex items-center gap-1">
                  <button className="min-w-0 flex-1 px-2 py-1 text-left hover:bg-surface" onClick={() => {
                    player.current.seek(c.start_ms);
                    player.current.play();
                  }}>
                    <span className="font-score text-xs">{t("clips.range", { start: gameAt(c.start_ms), end: gameAt(c.end_ms) })}</span>{" "}
                    {c.title}
                  </button>
                  {/* one scene as a link for the team chat (K20) */}
                  {staff && <ShareButton orgId={orgId} teamId={match.team_id} kind="scene" targetId={c.id} info={{ title: c.title ?? "" }} trigger={<Button size="icon-sm" variant="ghost" aria-label={t("share.dialogTitle", { kind: "scene" })} data-testid="clip-share"><Share2 aria-hidden /></Button>} />}
                </li>
              ))}
            </ul>
          </div>
        )}

        {tab === "drawings" && (
          <div role="tabpanel" className="flex min-h-0 flex-1 flex-col gap-3">
            {staff && !drawing && (
              <Button variant="secondary" onClick={startDrawing}>
                {t("draw.start")}
              </Button>
            )}
            {drawing && (
              <div className="space-y-2">
                <p className="text-xs text-muted">{t("draw.hint")}</p>
                <div className="flex flex-wrap gap-1" role="group" aria-label={t("draw.title")}>
                  {TOOLS.map((k) => (
                    <button
                      key={k}
                      aria-pressed={tool === k}
                      onClick={() => setTool(k)}
                      className={cn("border px-2 py-1 text-xs", tool === k ? "border-foreground bg-foreground text-background" : "border-border bg-raised hover:bg-surface")}
                    >
                      {t(`draw.tool_${k}`)}
                    </button>
                  ))}
                </div>
                <div className="flex gap-1" role="group" aria-label={t("draw.color")}>
                  {COLORS.map((c) => (
                    <button
                      key={c}
                      aria-label={c}
                      aria-pressed={color === c}
                      onClick={() => setColor(c)}
                      className={cn("size-7 rounded-full border-2", color === c ? "border-foreground" : "border-border")}
                      style={{ background: c }}
                    />
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button onClick={saveDrawing} disabled={shapes.length === 0}>
                    {t("draw.save")}
                  </Button>
                  <Button variant="ghost" onClick={() => (setShapes([]), setDrawing(false))}>
                    {t("draw.discard")}
                  </Button>
                </div>
              </div>
            )}
            <ul className="min-h-0 flex-1 space-y-1 overflow-auto text-sm">
              {(annotations.data ?? []).length === 0 && <li className="text-muted">{t("draw.empty")}</li>}
              {(annotations.data ?? []).map((a) => (
                <li key={a.id}>
                  <button className="px-2 py-1 font-score text-xs hover:bg-surface" onClick={() => {
                    player.current.pause();
                    player.current.seek(a.t_ms + 100);
                  }}>
                    {gameAt(a.t_ms)} · {a.shapes.length}×
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}

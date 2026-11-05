"use client";

import { track } from "@/lib/analytics";
import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Crosshair, Keyboard, Maximize2, Play, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, type FormEvent, type Ref } from "react";
import { useRouter } from "next/navigation";
import { CourtCalibration } from "@/components/analysis/court-calibration";
import { Tagger, useRosterNames } from "@/components/analysis/tagger";
import { FROM_VIDEO_KEY, playFromVideo } from "@/lib/play-from-video";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Segmented } from "@/components/ui/tabs";
import { control, Input, Select } from "@/components/ui/field";
import { SpotlightControls, useSpotlight } from "@/components/video/spotlight-controls";
import { SpotlightOverlay } from "@/components/video/spotlight";
import { MultiAngleControls, useMultiAngle } from "@/components/video/multi-angle";
import { SyncedCam } from "@/components/video/synced-cam";
import { cameraAt } from "@/lib/best-camera";
import { DrawLayer } from "@/components/video/draw-layer";
import { MiniCourt } from "@/components/video/mini-court";
import { VideoPlayer, type Marker, type PlayerHandle } from "@/components/video/player";
import type { Shape, Tool } from "@/components/video/shapes";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { coverage, firstOpen, steps } from "@/lib/match-workflow";
import { goalRows } from "@/lib/official-goals";
import { cn } from "@/lib/utils";
import { GoalCandidatesPanel, useGoalCandidates } from "./goal-candidates";
import { KickoffPanel } from "./kickoff-panel";
import { MatchTimeline } from "./match-timeline";
import { OfficialGoalsPanel, useOfficialGoals } from "./official-goals";
import { OfficialReportImport } from "./official-report";
import { WorkRail, type Pane } from "./work-rail";
import { useGameTime } from "./game-time";

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
  handle,
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
  handle?: Ref<PlayerHandle | null>;
}) {
  const t = useTranslations();
  const qc = useQueryClient();
  const router = useRouter();
  const raw = useRef<PlayerHandle>(null);
  // camera switch (M5): every time in this component is main-video time; other cameras are shifted
  // by their sync offset (time in that video = main time + offset)
  const cams = match.videos.filter((v) => v.status === "ready" && v.has_hls);
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
  const [activeCandidate, setActiveCandidate] = useState<string | null>(null);
  useEffect(() => {
    if (!reviewing) return;
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && setReviewing(false);
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

  const comments = useQuery({
    queryKey: ["comments", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/comments", { params: { path: m } })).data ?? [],
  });
  const clips = useQuery({
    queryKey: ["clips", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/clips", { params: { path: m } })).data ?? [],
  });
  const analysis = useQuery({
    queryKey: ["analysis", video.id],
    refetchInterval: (q) => (q.state.data?.status === "running" ? 10_000 : false),
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: orgId, video_id: video.id } } }))
        .data ?? null,
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
  const annotations = useQuery({
    queryKey: ["annotations", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/annotations", { params: { path: m } })).data ?? [],
  });
  const playlists = useQuery({
    queryKey: ["playlists", match.team_id],
    enabled: staff,
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/playlists", { params: { path: { org_id: orgId, team_id: match.team_id } } }))
        .data ?? [],
  });

  const markers: Marker[] = useMemo(
    () => [
      ...(comments.data ?? []).map((c) => ({ t_ms: c.t_ms, kind: "comment" as const, label: c.body })),
      ...(clips.data ?? []).map((c) => ({ t_ms: c.start_ms, kind: "clip" as const, label: c.title ?? "" })),
      ...(annotations.data ?? []).map((a) => ({ t_ms: a.t_ms, kind: "drawing" as const })),
    ],
    [comments.data, clips.data, annotations.data],
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
  const [spotOpen, setSpotOpen] = useState(false);
  const spotShown = spotOpen || spot.track != null || spot.picking;
  const multi = useMultiAngle(cams, video.id);
  const pickCam = multi.pick;
  const mainVideo = useCallback(() => raw.current?.video() ?? null, []);
  const events = useQuery({
    queryKey: ["events", match.id],
    // the auto camera and the events lane of the timeline
    enabled: (multi.auto && cams.length > 1) || staff,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/events", { params: { path: { org_id: orgId, match_id: match.id } } })).data ?? [],
  });
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
  const roster = useQuery({
    queryKey: ["roster-names", match.season_id],
    queryFn: async () =>
      (
        await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", {
          params: { path: { org_id: orgId, team_id: match.team_id, season_id: match.season_id } },
        })
      ).data ?? [],
  });
  const spotNames = Object.fromEntries((roster.data ?? []).map((r) => [r.player_id, `#${r.jersey_number ?? "?"} ${r.first_name}`]));
  const spotLabel = (() => {
    const tr = analysis.data?.tracks.find((x) => x.track_no === spot.track);
    return tr ? (tr.player_id && spotNames[tr.player_id]) || (tr.number != null ? `#${tr.number}` : "") : "";
  })();

  // the order of work: court, throw-off, goals, players; the lists share the panels' caches
  const hasReport = match.report_extra?.official_report != null;
  const candidates = useGoalCandidates(orgId, match.id, staff);
  const official = useOfficialGoals(orgId, match.id, staff && hasReport);
  const durationMs = video.duration_s ? video.duration_s * 1000 : null;
  const rate = candidates.data?.default_rate ?? 2;
  const a = analysis.data;
  const spansFor = coverage(match.kickoff_ms, match.period_s, video.duration_s ? video.duration_s * 1000 : null);
  const reportOpen = hasReport && official.data?.imported ? goalRows(official.data, "open", false, spansFor).length : null;
  const stepList = steps({
    analysis: a
      ? { status: a.status, needsCalibration: a.needs_calibration === true, unconfirmed: a.camera === "moving" && a.calibration?.source === "heuristic" }
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
  const tools: Pane[] = [...(staff ? (["events"] as const) : (["court"] as const)), ...(a?.status === "ready" ? (["formations"] as const) : []), "notes"];
  const chosen: Pane = pane ?? (staff ? (firstOpen(stepList) ?? "notes") : "notes");
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
  const shown: Pane = reviewing ? "goals" : chosen;
  const openNow = candidates.data?.counts.open_by_rate[String(rate)] ?? 0;
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
            {t("workflow.goals")}
          </h2>
          <span className="text-muted">{`${teamName} ${t("matches.vs")} ${oppName}`}</span>
          <span className="ml-auto font-score text-xl tabular-nums" aria-live="polite">
            {t("workflow.reviewLeft", { n: openNow })}
          </span>
          <Button variant="secondary" onClick={() => setReviewing(false)} data-testid="review-close">
            <X aria-hidden />
            {t("workflow.reviewClose")}
          </Button>
        </div>
      ) : (
        <WorkRail steps={staff ? stepList : []} tools={tools} value={shown} onChange={setPane} idPrefix={paneId} />
      )}
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_24rem] xl:grid-cols-[minmax(0,1fr)_27rem]">
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
            ) : spot.ready && !offset ? (
              <SpotlightOverlay
                baseUrl={`/v1/orgs/${orgId}/videos/${video.id}/tracks`}
                chunkMs={analysis.data!.chunk_ms!}
                homography={analysis.data!.calibration!.homography}
                imageSize={analysis.data!.calibration!.image_size as [number, number]}
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
          <span aria-hidden className="pointer-events-none absolute left-2 top-2 z-10 rounded-xs bg-black/65 px-2 py-0.5 font-score text-base text-white tabular-nums">
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
                ? "aspect-video w-full rounded"
                : autoCam && multi.mode === "single"
                  ? "pointer-events-none absolute inset-0 size-full object-contain"
                  : "pointer-events-none absolute right-2 top-2 w-1/3 rounded border-2 border-white shadow-lg",
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
          <details className="group relative">
            <summary className="inline-flex min-h-8 cursor-pointer list-none items-center gap-1.5 rounded-md px-3 text-[0.8125rem] font-medium text-muted hover:bg-surface hover:text-foreground [&::-webkit-details-marker]:hidden">
              <Keyboard aria-hidden className="size-4" />
              {t("player.shortcuts")}
            </summary>
            <p className="absolute left-0 z-20 mt-1 w-80 max-w-[85vw] rounded-md bg-raised p-3 text-xs leading-relaxed text-muted shadow-xl ring-1 ring-border">{t("player.shortcutsList")}</p>
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
          candidates={staff ? candidates.data : null}
          rate={rate}
          activeId={shown === "goals" ? activeCandidate : null}
          events={staff ? events.data : null}
          notes={[...(comments.data ?? []).map((c) => c.t_ms), ...(clips.data ?? []).map((c) => c.start_ms), ...(annotations.data ?? []).map((x) => x.t_ms)]}
          onSetKickoff={staff ? () => setPane("kickoff") : undefined}
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
        role={reviewing ? undefined : "tabpanel"}
        aria-labelledby={reviewing ? undefined : `${paneId}-tab-${shown}`}
        className="flex min-w-0 flex-col gap-4 lg:sticky lg:top-4 lg:max-h-[calc(100dvh-2rem)] lg:overflow-y-auto lg:pr-1"
      >
        {shown === "court" && (
          <>
            <AnalysisPanel analysis={a ?? null} orgId={orgId} videoId={video.id} colours={kitColours} getTime={getTime} canCalibrate={staff} />
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
                className="max-lg:order-last"
                label={t("workflow.goalLists")}
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
              <Button variant="secondary" className="self-start max-lg:order-last" onClick={() => (setGoalList("candidates"), setReviewing(true))} data-testid="review-open">
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
        {shown === "formations" && a?.status === "ready" && <FormationsCard formations={a.formations ?? []} onSeek={jump} />}
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
                <li key={c.id} className="rounded-md bg-surface px-3 py-2">
                  <button className="rounded-md bg-accent/10 px-2 py-0.5 text-xs font-semibold text-accent tabular-nums hover:bg-accent/20" onClick={() => player.current.seek(c.t_ms)}>
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
                <li key={c.id}>
                  <button className="w-full rounded px-2 py-1 text-left hover:bg-surface" onClick={() => {
                    player.current.seek(c.start_ms);
                    player.current.play();
                  }}>
                    <span className="font-score text-xs">{t("clips.range", { start: gameAt(c.start_ms), end: gameAt(c.end_ms) })}</span>{" "}
                    {c.title}
                  </button>
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
                      className={cn("rounded-md border px-2 py-1 text-xs", tool === k ? "border-foreground bg-foreground text-background" : "border-border bg-raised hover:bg-surface")}
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
                  <button className="rounded px-2 py-1 font-score text-xs hover:bg-surface" onClick={() => {
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

type Analysis = Schemas["AnalysisOut"];

function AnalysisPanel({
  analysis,
  orgId,
  videoId,
  colours,
  getTime,
  canCalibrate,
}: {
  analysis: Analysis | null;
  orgId: string;
  videoId: string;
  colours: Record<string, string>;
  getTime: () => number;
  canCalibrate: boolean;
}) {
  const t = useTranslations("analysis");
  const [marking, setMarking] = useState(false);
  const ready = analysis?.status === "ready";
  useEffect(() => {
    if (ready) track("analysis_viewed");
  }, [ready]);
  if (!analysis || analysis.status === "none") return null;
  const canMark = canCalibrate && analysis.status === "ready" && analysis.panorama != null;
  const unconfirmed = analysis.camera === "moving" && analysis.calibration?.source === "heuristic";
  return (
    <section className="space-y-3" data-testid="analysis-panel">
      <h2 className="sr-only">{t("title")}</h2>
      {analysis.status === "running" && <p className="text-sm">{t("running")}</p>}
      {analysis.status === "failed" && (
        <Alert>
          <span className="block font-medium">{t(`failure_${analysis.error_code ?? "generic"}` as "failure_generic")}</span>
          <span className="block">{t(`failureNext_${analysis.error_code ?? "generic"}` as "failureNext_generic")}</span>
          <span className="block text-xs">{t("failureCredit")}</span>
        </Alert>
      )}
      {analysis.status === "ready" && analysis.needs_calibration && (
        <Alert kind="info">{t(canMark ? "needsCalibration" : "needsCalibrationStaff")}</Alert>
      )}
      {/* one sentence: does the court fit */}
      {analysis.status === "ready" && !analysis.needs_calibration && (
        <p className="text-[0.9375rem]">{unconfirmed ? t("checkCourt") : t("courtOk")}</p>
      )}
      {canMark && (
        <Button
          variant={analysis.needs_calibration ? "primary" : "secondary"}
          size={analysis.needs_calibration || unconfirmed ? "md" : "sm"}
          onClick={() => setMarking(true)}
          data-testid="mark-court"
        >
          {t(analysis.needs_calibration ? "markCourt" : unconfirmed ? "checkCourtButton" : "realign")}
        </Button>
      )}
      {marking && <CourtCalibration orgId={orgId} videoId={videoId} analysis={analysis} onClose={() => setMarking(false)} />}
      {analysis.chunks != null && analysis.chunk_ms != null && analysis.chunks > 0 && (
        <MiniCourt
          baseUrl={`/v1/orgs/${orgId}/videos/${videoId}/tracks`}
          chunkMs={analysis.chunk_ms}
          chunks={analysis.chunks}
          tracks={analysis.tracks}
          colours={colours}
          getTime={getTime}
          label={t("title")}
        />
      )}
      <div className="flex flex-wrap gap-3 text-xs text-muted">
        {(["home", "away", "referee"] as const).map((k) => (
          <span key={k} className="flex items-center gap-1">
            <span aria-hidden className="inline-block size-3 rounded-full ring-1 ring-foreground/50" style={{ background: colours[k] }} />
            {t(k)}
          </span>
        ))}
      </div>
      {/* what the analysis did, for those who want to know; not a coach's task */}
      <details className="text-xs text-muted">
        <summary className="cursor-pointer hover:text-foreground">{t("technical")}</summary>
        <div className="mt-2 space-y-1.5">
          {analysis.detector === "heuristic" && <p title={t("heuristicHint")}>{t("heuristic")}</p>}
          {analysis.auto_events && (
            <p data-testid="auto-events">
              {(analysis.auto_events.missing as string[] | undefined)?.includes("goalkeepers")
                ? t("autoNoGoalkeepers")
                : t("autoSummary", { events: Number(analysis.auto_events.events ?? 0), possessions: Number(analysis.auto_events.possessions ?? 0) })}{" "}
              {t("autoLimits")}
              {Number(analysis.auto_events.overlay_goals ?? 0) > 0 && (
                <span className="block" data-testid="overlay-goals">
                  {t("autoOverlay", { goals: Number(analysis.auto_events.overlay_goals) })}
                </span>
              )}
            </p>
          )}
          {analysis.calibration && (
            <p>
              {t("calibration")}: {t(`calibration_${analysis.calibration.source as "heuristic"}`)},{" "}
              {t("confidence", { value: Math.round(analysis.calibration.confidence * 100) })}
            </p>
          )}
          {analysis.tracks.length > 0 && <p>{t("tracks", { count: analysis.tracks.length })}</p>}
        </div>
      </details>
    </section>
  );
}

/** Own-team tracks worth naming: the longest 40. */
function ownTracks(tracks: Analysis["tracks"]) {
  return tracks
    .filter((tr) => tr.team === "home" || tr.team === "home_gk")
    .sort((a, b) => b.last_ms - b.first_ms - (a.last_ms - a.first_ms))
    .slice(0, 40);
}


/** Manual track identities (M5): own-team tracks to roster players; kept across re-analysis. */
function IdentityPanel({
  orgId,
  match,
  videoId,
  tracks,
  onSeek,
  at,
}: {
  orgId: string;
  match: Match;
  videoId: string;
  tracks: Analysis["tracks"];
  onSeek: (ms: number) => void;
  at: (videoMs: number) => string;
}) {
  const t = useTranslations("identity");
  const qc = useQueryClient();
  const roster = useRosterNames(orgId, match.team_id, match.season_id);
  const [notice, setNotice] = useState<string | null>(null);
  const [all, setAll] = useState(false);
  // in the order they appear, so the coach goes through the video once
  const own = [...ownTracks(tracks)].sort((a, b) => a.first_ms - b.first_ms);
  const open = own.filter((tr) => !tr.player_id);
  // the next open people first; the whole list on request
  // a few seconds on screen is rarely worth a name: those fold away with the rest
  const long = open.filter((tr) => tr.last_ms - tr.first_ms >= 5000);
  const shown = all ? own : [...long.slice(0, 8), ...own.filter((tr) => tr.player_id)].sort((a, b) => a.first_ms - b.first_ms);
  if (own.length === 0) return null;
  async function assign(trackNo: number, playerId: string) {
    const { error } = await api.PUT("/v1/orgs/{org_id}/videos/{video_id}/tracks/{track_no}/identity", {
      params: { path: { org_id: orgId, video_id: videoId, track_no: trackNo } },
      body: { player_id: playerId || null, number: null },
    });
    if (!error) {
      setNotice(t("saved"));
      void qc.invalidateQueries({ queryKey: ["analysis", videoId] });
      void qc.invalidateQueries({ queryKey: ["physical", match.id] });
    }
  }
  return (
    <section data-testid="identity-panel" aria-labelledby="identity-title">
        <h2 id="identity-title" className="font-display text-xl">{t("title")}</h2>
        <p className="mt-1 text-sm">
          {open.length > 0 ? t("openCount", { n: open.length, first: at(open[0]!.first_ms) }) : t("allDone")}
        </p>
        <p className="mt-1 text-xs text-muted">{t("hint")}</p>
        <ul className="mt-3 divide-y divide-border/70 text-sm">
          {shown.map((tr) => (
            <li key={tr.track_no} className="flex flex-wrap items-center gap-2 py-1.5">
              <Button variant="quiet" size="sm" className="min-w-0 justify-start" onClick={() => onSeek(tr.first_ms + 500)} aria-label={`${t("seek")}: ${t("track", { n: tr.track_no })}, ${at(tr.first_ms)}`}>
                <Play aria-hidden className="size-3 fill-current" />
                <span className="font-score tabular-nums">{at(tr.first_ms)}</span>
                {/* a shirt number the analysis read helps to recognise the person; the track id does not */}
                <span className="text-muted">
                  {tr.number != null ? t("shirt", { n: tr.number }) : t("track", { n: tr.track_no })}
                  {` · ${t("onScreen", { s: Math.round((tr.last_ms - tr.first_ms) / 1000) })}`}
                </span>
              </Button>
              <label className="sr-only" htmlFor={`track-${tr.track_no}`}>
                {t("track", { n: tr.track_no })}
              </label>
              <select
                id={`track-${tr.track_no}`}
                value={tr.player_id ?? ""}
                onChange={(e) => void assign(tr.track_no, e.target.value)}
                className="min-h-9 flex-1 rounded-md bg-raised ring-1 ring-inset ring-border px-2"
              >
                <option value="">{t("none")}</option>
                {(roster.data ?? [])
                  .filter((r) => r.active)
                  .map((r) => (
                    <option key={r.player_id} value={r.player_id}>
                      {r.jersey_number != null ? `#${r.jersey_number} ` : ""}
                      {r.first_name} {r.last_name}
                    </option>
                  ))}
              </select>
              {tr.identity_source && <span className="text-xs text-muted">{tr.identity_source === "model" ? t("auto") : t("manual")}</span>}
            </li>
          ))}
        </ul>
        {own.length > shown.length && (
          <Button variant="ghost" size="sm" className="mt-1" onClick={() => setAll(true)}>
            {t("showAll", { n: own.length })}
          </Button>
        )}
        {notice && (
          <p className="mt-2 text-xs text-ok" aria-live="polite">
            {notice}
          </p>
        )}
    </section>
  );
}


function CameraSwitch({
  orgId,
  cams,
  active,
  staff,
  onSwitch,
}: {
  orgId: string;
  cams: Video[];
  active: Video;
  staff: boolean;
  onSwitch: (id: string) => void;
}) {
  const t = useTranslations("camera");
  const qc = useQueryClient();
  const sync = active.sync;
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="camera-switch">
      <span className="font-medium">{t("label")}:</span>
      <div role="group" aria-label={t("label")} className="flex flex-wrap gap-1">
        {cams.map((c) => (
          <button
            key={c.id}
            aria-pressed={c.id === active.id}
            onClick={() => onSwitch(c.id)}
            className={cn("rounded-md border px-2 py-1", c.id === active.id ? "border-foreground bg-foreground text-background" : "border-border bg-raised hover:bg-surface")}
          >
            {t(c.role)}
          </button>
        ))}
      </div>
      {active.role !== "main" && sync?.source === "audio" && sync.applied && (
        <span className="text-xs text-muted">{t("synced", { confidence: Math.round((sync.confidence ?? 0) * 100) })}</span>
      )}
      {active.role !== "main" && sync?.source === "user_correction" && <span className="text-xs text-muted">{t("manual")}</span>}
      {active.role !== "main" && (!sync || (sync.source === "audio" && !sync.applied)) && (
        <span className="text-xs text-accent">{t("syncLow")}</span>
      )}
      {staff && active.role !== "main" && (
        <form
          className="flex items-end gap-1"
          onSubmit={async (e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const value = Number(new FormData(form).get("offset"));
            await api.PATCH("/v1/orgs/{org_id}/videos/{video_id}", {
              params: { path: { org_id: orgId, video_id: active.id } },
              body: { time_offset_ms: value },
            });
            void qc.invalidateQueries({ queryKey: ["match"] });
          }}
        >
          <label className="flex flex-col text-xs">
            {t("offset")}
            <input
              name="offset"
              type="number"
              step={10}
              defaultValue={active.time_offset_ms}
              key={active.id}
              className="min-h-9 w-28 rounded-md bg-raised ring-1 ring-inset ring-border px-2 text-sm"
            />
          </label>
          <Button type="submit" variant="secondary" className="min-h-9 px-2 text-xs">
            {t("save")}
          </Button>
        </form>
      )}
    </div>
  );
}


/** Defence systems per team over time (heuristic from positions, M6). */
function FormationsCard({ formations, onSeek }: { formations: NonNullable<Analysis["formations"]>; onSeek: (ms: number) => void }) {
  const t = useTranslations("formations");
  const label = (f: string) => (f === "open" ? t("open") : f.replaceAll("-", ":"));
  return (
    <section className="space-y-2" data-testid="formations">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold">{t("title")}</h2>
        <p className="text-xs text-muted">{t("hint")}</p>
      </div>
      {formations.length === 0 && <p className="text-sm text-muted">{t("none")}</p>}
      {(["home", "away"] as const).map((team) => {
        const segs = formations.filter((f) => f.team === team);
        if (segs.length === 0) return null;
        const total = segs.reduce((s, f) => s + f.end_ms - f.start_ms, 0);
        const share = Object.entries(
          segs.reduce<Record<string, number>>((acc, f) => ({ ...acc, [f.formation]: (acc[f.formation] ?? 0) + f.end_ms - f.start_ms }), {}),
        ).sort((a, b) => b[1] - a[1]);
        return (
          <div key={team} className="space-y-1 text-sm">
            <p>
              <span className="font-medium">{team === "home" ? t("own") : t("opponent")}: </span>
              {share.map(([f, ms]) => `${label(f)} ${Math.round((ms / total) * 100)} %`).join(" · ")}
            </p>
            <ul className="flex flex-wrap gap-1">
              {segs.map((f) => (
                <li key={`${f.start_ms}-${f.team}`}>
                  <button
                    className="rounded bg-surface px-2 py-0.5 font-score text-xs hover:brightness-90"
                    onClick={() => onSeek(f.start_ms)}
                    aria-label={t("jump", { formation: label(f.formation), time: formatClock(f.start_ms) })}
                  >
                    {formatClock(f.start_ms)} {label(f.formation)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </section>
  );
}

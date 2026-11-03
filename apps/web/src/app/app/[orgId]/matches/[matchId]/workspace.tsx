"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useCallback, useImperativeHandle, useMemo, useRef, useState, type FormEvent, type Ref } from "react";
import { Tagger, useRosterNames } from "@/components/analysis/tagger";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { DrawLayer } from "@/components/video/draw-layer";
import { MiniCourt } from "@/components/video/mini-court";
import { VideoPlayer, type Marker, type PlayerHandle } from "@/components/video/player";
import type { Shape, Tool } from "@/components/video/shapes";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";

type Match = Schemas["MatchOut"];
type Video = Schemas["VideoOut"];
type Tab = "comments" | "clips" | "drawings" | "events";
const TOOLS: Tool[] = ["arrow", "line", "circle", "freehand", "spotlight"];
const COLORS = ["#facc15", "#ef4444", "#22c55e", "#3b82f6", "#ffffff"];

export function Workspace({
  orgId,
  match,
  video,
  staff,
  teamName,
  handle,
}: {
  orgId: string;
  match: Match;
  video: Video;
  staff: boolean;
  teamName: string;
  handle?: Ref<PlayerHandle | null>;
}) {
  const t = useTranslations();
  const qc = useQueryClient();
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
    () => ({ home: match.kit_own, home_gk: match.kit_own_gk, away: match.kit_opponent, away_gk: match.kit_opponent_gk, referee: "#111827" }),
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

  const onKey = useCallback(
    (key: string) => {
      if (!staff) return false;
      const ms = player.current.time() ?? 0;
      if (key === "i") return setMarkIn(ms), setTab("clips"), true;
      if (key === "o") return setMarkOut(ms), setTab("clips"), true;
      if (key === "d") return startDrawing(), true;
      return false;
    },
    [staff, startDrawing],
  );

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-2">
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
          overlay={drawing ? <DrawLayer tool={tool} color={color} shapes={shapes} onChange={setShapes} /> : undefined}
        />
        {cams.length > 1 && <CameraSwitch orgId={orgId} cams={cams} active={cam} staff={staff} onSwitch={switchCamera} />}
        <p className="text-xs text-muted">{t("player.shortcutsList")}</p>
        <AnalysisPanel analysis={analysis.data ?? null} orgId={orgId} videoId={video.id} colours={kitColours} getTime={getTime} />
        {staff && analysis.data?.status === "ready" && (
          <IdentityPanel
            orgId={orgId}
            match={match}
            videoId={video.id}
            tracks={analysis.data.tracks}
            onSeek={(ms) => {
              player.current.pause();
              player.current.seek(ms);
            }}
          />
        )}
        {failure && <Alert className="py-2">{t(`errors.${failure}`)}</Alert>}
        {notice && (
          <Alert kind="success" className="py-2">
            {notice}
          </Alert>
        )}
      </div>

      <Card className="flex max-h-[42rem] flex-col gap-3 p-3">
        <div role="tablist" className="flex gap-1">
          {(staff ? (["comments", "clips", "drawings", "events"] as const) : (["comments", "clips", "drawings"] as const)).map((k) => (
            <button
              key={k}
              role="tab"
              aria-selected={tab === k}
              onClick={() => setTab(k)}
              className={cn("flex-1 rounded px-2 py-1.5 text-sm", tab === k ? "bg-accent text-accent-contrast" : "hover:bg-surface")}
            >
              {t(k === "drawings" ? "draw.list" : k === "events" ? "events.title" : `${k}.title`)}
            </button>
          ))}
        </div>

        {tab === "events" && staff && (
          <div role="tabpanel" className="flex min-h-0 flex-1 flex-col">
            <Tagger orgId={orgId} match={match} teamName={teamName} getTime={getTime} />
          </div>
        )}

        {tab === "comments" && (
          <div role="tabpanel" className="flex min-h-0 flex-1 flex-col gap-2">
            <ul className="min-h-0 flex-1 space-y-2 overflow-auto text-sm" data-testid="comments">
              {(comments.data ?? []).length === 0 && <li className="text-muted">{t("comments.empty")}</li>}
              {(comments.data ?? []).map((c) => (
                <li key={c.id} className="rounded bg-surface p-2">
                  <button className="font-mono text-xs text-accent underline" onClick={() => player.current.seek(c.t_ms)}>
                    {formatClock(c.t_ms)}
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
                {t("comments.placeholder", { time: formatClock(now) })}
              </label>
              <input
                id="comment-body"
                name="body"
                maxLength={2000}
                placeholder={t("comments.placeholder", { time: formatClock(now) })}
                className="min-h-10 flex-1 rounded-md border border-border bg-background px-3 text-sm"
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
                    <span className="font-mono text-xs">{t("clips.range", { start: formatClock(c.start_ms), end: formatClock(c.end_ms) })}</span>{" "}
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
                      className={cn("rounded border px-2 py-1 text-xs", tool === k ? "border-accent bg-accent text-accent-contrast" : "border-border")}
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
                  <button className="rounded px-2 py-1 font-mono text-xs hover:bg-surface" onClick={() => {
                    player.current.pause();
                    player.current.seek(a.t_ms + 100);
                  }}>
                    {formatClock(a.t_ms)} · {a.shapes.length}×
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>
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
}: {
  analysis: Analysis | null;
  orgId: string;
  videoId: string;
  colours: Record<string, string>;
  getTime: () => number;
}) {
  const t = useTranslations("analysis");
  if (!analysis || analysis.status === "none") return null;
  return (
    <Card className="space-y-3 p-3" data-testid="analysis-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">{t("title")}</h2>
        {analysis.detector === "heuristic" && (
          <span className="rounded-full bg-surface px-2 py-0.5 text-xs" title={t("heuristicHint")}>
            {t("heuristic")}
          </span>
        )}
      </div>
      {analysis.status === "running" && <p className="text-sm text-muted">{t("running")}</p>}
      {analysis.status === "failed" && <Alert>{t("failed", { error: analysis.error ?? "" })}</Alert>}
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
            <span aria-hidden className="inline-block size-3 rounded-full border border-neutral-700" style={{ background: colours[k] }} />
            {t(k)}
          </span>
        ))}
        {analysis.calibration && (
          <span>
            {t("calibration")}: {t(`calibration_${analysis.calibration.source as "heuristic"}`)},{" "}
            {t("confidence", { value: Math.round(analysis.calibration.confidence * 100) })}
          </span>
        )}
        {analysis.tracks.length > 0 && <span>{t("tracks", { count: analysis.tracks.length })}</span>}
      </div>
    </Card>
  );
}


/** Manual track identities (M5): own-team tracks to roster players; kept across re-analysis. */
function IdentityPanel({
  orgId,
  match,
  videoId,
  tracks,
  onSeek,
}: {
  orgId: string;
  match: Match;
  videoId: string;
  tracks: Analysis["tracks"];
  onSeek: (ms: number) => void;
}) {
  const t = useTranslations("identity");
  const qc = useQueryClient();
  const roster = useRosterNames(orgId, match.team_id, match.season_id);
  const [notice, setNotice] = useState<string | null>(null);
  const own = tracks
    .filter((tr) => tr.team === "home" || tr.team === "home_gk")
    .sort((a, b) => b.last_ms - b.first_ms - (a.last_ms - a.first_ms))
    .slice(0, 40);
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
    <Card className="p-3" data-testid="identity-panel">
      <details>
        <summary className="cursor-pointer font-semibold">{t("title")}</summary>
        <p className="mt-2 text-xs text-muted">{t("hint")}</p>
        <ul className="mt-2 max-h-72 space-y-1 overflow-auto text-sm">
          {own.map((tr) => (
            <li key={tr.track_no} className="flex flex-wrap items-center gap-2">
              <button className="w-36 text-left font-mono text-xs underline" onClick={() => onSeek(tr.first_ms + 500)} aria-label={`${t("seek")}: ${t("track", { n: tr.track_no })}`}>
                {t("track", { n: tr.track_no })} · {formatClock(tr.first_ms)}
              </button>
              <label className="sr-only" htmlFor={`track-${tr.track_no}`}>
                {t("track", { n: tr.track_no })}
              </label>
              <select
                id={`track-${tr.track_no}`}
                value={tr.player_id ?? ""}
                onChange={(e) => void assign(tr.track_no, e.target.value)}
                className="min-h-9 flex-1 rounded-md border border-border bg-background px-2"
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
        {notice && (
          <p className="mt-2 text-xs text-ok" aria-live="polite">
            {notice}
          </p>
        )}
      </details>
    </Card>
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
            className={cn("rounded border px-2 py-1", c.id === active.id ? "border-accent bg-accent text-accent-contrast" : "border-border")}
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
              className="min-h-9 w-28 rounded-md border border-border bg-background px-2 text-sm"
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

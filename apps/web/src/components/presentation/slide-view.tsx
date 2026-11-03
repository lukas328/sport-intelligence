"use client";

import type { Schemas } from "@handball/api-client";
import type { Frame } from "@handball/tactics";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Board } from "@/components/tactics/board";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import type { Shape } from "@/components/video/shapes";
import { api } from "@/lib/client";

export type Slide = Schemas["SlideOut"];
type Hold = { t_ms: number; duration_ms?: number; shapes?: Shape[] };
type Slow = { from_ms: number; to_ms: number; rate?: number };

/** Shapes (normalised 0..1) as SVG on top of the video, same look as the player drawings. */
export function ShapesOverlay({ shapes }: { shapes: Shape[] }) {
  return (
    <svg viewBox="0 0 1000 562" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 size-full" aria-hidden>
      <defs>
        <marker id="pres-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="context-stroke" />
        </marker>
      </defs>
      {shapes.map((s, i) => {
        const pts = s.points.map(([x, y]) => [x * 1000, y * 562] as const);
        const a = pts[0];
        const b = pts[pts.length - 1];
        if (!a || !b) return null;
        const w = s.width + 1;
        if (s.kind === "circle" || s.kind === "spotlight")
          return <ellipse key={i} cx={(a[0] + b[0]) / 2} cy={(a[1] + b[1]) / 2} rx={Math.abs(b[0] - a[0]) / 2 || 20} ry={Math.abs(b[1] - a[1]) / 2 || 20} fill="none" stroke={s.color} strokeWidth={w} />;
        if (s.kind === "text")
          return (
            <text key={i} x={a[0]} y={a[1]} fill={s.color} fontSize={28} fontWeight={700}>
              {s.text}
            </text>
          );
        if (s.kind === "freehand") return <polyline key={i} points={pts.map((p) => p.join(",")).join(" ")} fill="none" stroke={s.color} strokeWidth={w} strokeLinecap="round" />;
        return <line key={i} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={s.color} strokeWidth={w} strokeLinecap="round" markerEnd={s.kind === "arrow" ? "url(#pres-arrow)" : undefined} />;
      })}
    </svg>
  );
}

/** Clip slide: plays the window, slows down in slow-motion ranges, stops at hold points with drawings. */
function ClipSlide({ orgId, c, paused, extraShapes, onEnd }: { orgId: string; c: Record<string, unknown>; paused: boolean; extraShapes: Shape[]; onEnd?: (() => void) | undefined }) {
  const ref = useRef<PlayerHandle>(null);
  const holds = (c.holds as Hold[] | undefined) ?? [];
  const slow = (c.slow as Slow[] | undefined) ?? [];
  const done = useRef(new Set<number>());
  const [holding, setHolding] = useState<Hold | null>(null);
  useEffect(() => {
    const v = ref.current?.video();
    if (!v) return;
    if (paused) v.pause();
    else if (!holding) void v.play().catch(() => undefined);
  }, [paused, holding]);
  function onTime(ms: number) {
    const v = ref.current?.video();
    if (!v) return;
    const range = slow.find((s) => ms >= s.from_ms && ms < s.to_ms);
    const rate = range ? (range.rate ?? 0.5) : 1;
    if (v.playbackRate !== rate) v.playbackRate = rate;
    const hold = holds.find((h) => ms >= h.t_ms && ms < h.t_ms + 400 && !done.current.has(h.t_ms));
    if (hold) {
      done.current.add(hold.t_ms);
      v.pause();
      setHolding(hold);
      window.setTimeout(() => {
        setHolding(null);
        void v.play().catch(() => undefined);
      }, hold.duration_ms ?? 3000);
    }
  }
  return (
    <VideoPlayer
      ref={ref}
      src={`/v1/orgs/${orgId}/videos/${String(c.video_id)}/media/hls/master.m3u8`}
      window={{ start_ms: Number(c.in_ms), end_ms: Number(c.out_ms) }}
      onTime={onTime}
      onWindowEnd={onEnd}
      autoPlay={!paused}
      overlay={<ShapesOverlay shapes={[...(holding?.shapes ?? []), ...extraShapes]} />}
    />
  );
}

function PlaySlide({ orgId, playId }: { orgId: string; playId: string }) {
  const t = useTranslations("presentations");
  const q = useQuery({
    queryKey: ["play", playId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/plays/{play_id}", { params: { path: { org_id: orgId, play_id: playId } } })).data,
  });
  const [i, setI] = useState(0);
  const doc = q.data?.doc as { court?: "half" | "full"; frames?: Frame[] } | undefined;
  const frames = doc?.frames ?? [];
  const frame = frames[i];
  if (!q.data || !frame) return null;
  return (
    <div className="space-y-2">
      <p className="text-xl font-semibold">{q.data.name}</p>
      <Board frame={frame} court={doc?.court ?? "half"} label={q.data.name} className="max-h-[70vh] w-full" />
      {frames.length > 1 && (
        <div className="flex justify-center gap-2">
          {frames.map((_, n) => (
            <button key={n} type="button" aria-pressed={n === i} onClick={() => setI(n)} className="rounded border border-border px-3 py-1 text-sm">
              {t("step", { n: n + 1 })}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function SlideView({
  orgId,
  slide,
  paused = false,
  extraShapes = [],
  onEnd,
  observationText,
}: {
  orgId: string;
  slide: Slide;
  paused?: boolean;
  extraShapes?: Shape[];
  onEnd?: () => void;
  observationText?: (o: Record<string, unknown>) => string;
}) {
  const c = slide.content as Record<string, unknown>;
  if (slide.type === "clip" && c.video_id) return <ClipSlide key={slide.id} orgId={orgId} c={c} paused={paused} extraShapes={extraShapes} onEnd={onEnd} />;
  if (slide.type === "tactics_board" && slide.play_id) return <PlaySlide orgId={orgId} playId={slide.play_id} />;
  if (slide.type === "image")
    return (
      <figure className="space-y-2 text-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`/v1/orgs/${orgId}/slides/${slide.id}/image`} alt={String(c.caption ?? "")} className="mx-auto max-h-[70vh]" />
        {Boolean(c.caption) && <figcaption>{String(c.caption)}</figcaption>}
      </figure>
    );
  const rows = (c.rows as { label: string; value: unknown; n?: number | null }[] | undefined) ?? [];
  const obs = c.observation as Record<string, unknown> | undefined;
  return (
    <div className="flex min-h-[50vh] flex-col justify-center gap-4 px-6">
      {Boolean(c.title) && <h2 className="text-4xl font-semibold">{String(c.title)}</h2>}
      {obs && observationText && <p className="text-3xl">{observationText(obs)}</p>}
      {Boolean(c.body) && <p className="whitespace-pre-line text-2xl">{String(c.body)}</p>}
      {rows.length > 0 && (
        <dl className="grid gap-3 sm:grid-cols-3">
          {rows.map((r) => (
            <div key={r.label} className="rounded-lg border border-border p-4">
              <dt className="text-sm text-muted">{r.label}</dt>
              <dd className="text-3xl font-semibold tabular-nums">{String(r.value ?? "-")}</dd>
              {r.n != null && <dd className="text-xs text-muted">n = {r.n}</dd>}
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

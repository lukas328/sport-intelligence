"use client";

import { COURT } from "@handball/court";
import { useEffect, useRef } from "react";

export interface TrackMeta {
  track_no: number;
  team: string | null;
}

type Chunk = Float32Array; // rows [t_ms, track, x, y]

/** Canvas mini court with live positions from the tracking data, synced to the video time.
 * Data is loaded in 30 s binary chunks (BRIEF 6.4) and drawn in its own animation frame loop,
 * so the surrounding React tree does not re-render with every video frame. */
export function MiniCourt({
  baseUrl,
  chunkMs,
  chunks,
  tracks,
  colours,
  getTime,
  label,
}: {
  baseUrl: string;
  chunkMs: number;
  chunks: number;
  tracks: TrackMeta[];
  colours: Record<string, string>;
  getTime: () => number;
  label: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cache = useRef(new Map<number, Chunk | "loading">());
  const teamOf = useRef(new Map<number, string | null>());

  useEffect(() => {
    teamOf.current = new Map(tracks.map((t) => [t.track_no, t.team]));
  }, [tracks]);

  useEffect(() => {
    const load = (n: number) => {
      if (n < 0 || n >= chunks || cache.current.has(n)) return;
      cache.current.set(n, "loading");
      void fetch(`${baseUrl}/${n}`, { credentials: "same-origin" })
        .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(String(r.status)))))
        .then((buf) => cache.current.set(n, new Float32Array(buf)))
        .catch(() => cache.current.delete(n));
    };
    let raf = 0;
    const pad = 1.5;
    const draw = () => {
      raf = requestAnimationFrame(draw);
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !ctx) return;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (canvas.width !== w * devicePixelRatio) {
        canvas.width = w * devicePixelRatio;
        canvas.height = h * devicePixelRatio;
      }
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      const sx = w / (COURT.length + 2 * pad);
      const sy = h / (COURT.width + 2 * pad);
      const X = (x: number) => (x + pad) * sx;
      const Y = (y: number) => h - (y + pad) * sy;
      // the court tokens follow the theme (a light court glares in dark mode)
      const css = getComputedStyle(canvas);
      ctx.fillStyle = css.getPropertyValue("--court").trim() || "#e6f0e8";
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = css.getPropertyValue("--court-line").trim() || "#1f2937";
      ctx.lineWidth = 1;
      for (const [name, pts] of Object.entries(COURT.lines)) {
        ctx.setLineDash(COURT.dashedLines.includes(name) ? [3, 3] : []);
        ctx.beginPath();
        pts.forEach(([x, y], i) => (i ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y))));
        ctx.stroke();
      }
      ctx.setLineDash([]);
      const t = getTime();
      const n = Math.floor(t / chunkMs);
      load(n);
      load(n + 1);
      const chunk = cache.current.get(n);
      if (!(chunk instanceof Float32Array)) return;
      // positions at the closest frame not after t, per track
      const latest = new Map<number, [number, number, number]>();
      for (let i = 0; i < chunk.length; i += 4) {
        const ts = chunk[i]!;
        if (ts > t || t - ts > 200) continue;
        const id = chunk[i + 1]!;
        const prev = latest.get(id);
        if (!prev || ts >= prev[0]) latest.set(id, [ts, chunk[i + 2]!, chunk[i + 3]!]);
      }
      for (const [id, [, x, y]] of latest) {
        const team = teamOf.current.get(id) ?? null;
        ctx.beginPath();
        ctx.arc(X(x), Y(y), team === "referee" ? 3 : 5, 0, Math.PI * 2);
        ctx.fillStyle = team ? (colours[team] ?? "#6b7280") : "#6b7280";
        ctx.fill();
        ctx.strokeStyle = "#111827";
        ctx.stroke();
      }
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [baseUrl, chunkMs, chunks, colours, getTime]);

  return <canvas ref={canvasRef} role="img" aria-label={label} className="aspect-[43/23] w-full" data-testid="mini-court" />;
}

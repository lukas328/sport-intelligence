"use client";

import { useEffect, useRef, useState, type MouseEvent } from "react";
import { nearestTrack, positionAt, project, trackSamples, trail, type Homography, type Sample } from "@/lib/spotlight";

interface Props {
  baseUrl: string; // .../videos/{id}/tracks
  chunkMs: number;
  homography: Homography;
  imageSize: [number, number];
  track: number | null;
  label: string;
  getTime: () => number;
  dim?: boolean;
  showTrail?: boolean;
  picking?: boolean;
  onPick?: (track: number | null) => void;
}

/** Canvas overlay: ring under the feet, label, optional dimmed surroundings and trail (4.2). */
export function SpotlightOverlay({ baseUrl, chunkMs, homography, imageSize, track, label, getTime, dim, showTrail, picking, onPick }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const chunks = useRef(new Map<number, Float32Array | "loading">());
  const [, force] = useState(0);

  function rowsAt(t: number): Float32Array | null {
    const n = Math.floor(t / chunkMs);
    const hit = chunks.current.get(n);
    if (hit instanceof Float32Array) return hit;
    if (!hit) {
      chunks.current.set(n, "loading");
      void fetch(`${baseUrl}/${n}`, { credentials: "same-origin" })
        .then((r) => (r.ok ? r.arrayBuffer() : null))
        .then((buf) => {
          if (buf) chunks.current.set(n, new Float32Array(buf));
          else chunks.current.delete(n);
          force((x) => x + 1);
        });
    }
    return null;
  }

  useEffect(() => {
    let raf = 0;
    let cache: { n: number; track: number; samples: Sample[] } | null = null;
    const draw = () => {
      raf = requestAnimationFrame(draw);
      const c = canvas.current;
      if (!c) return;
      const w = (c.width = c.clientWidth * devicePixelRatio);
      const h = (c.height = c.clientHeight * devicePixelRatio);
      const ctx = c.getContext("2d")!;
      ctx.clearRect(0, 0, w, h);
      if (track == null) return;
      const t = getTime();
      const rows = rowsAt(t);
      if (!rows) return;
      const n = Math.floor(t / chunkMs);
      if (!cache || cache.n !== n || cache.track !== track) cache = { n, track, samples: trackSamples(rows, track) };
      const pos = positionAt(cache.samples, t);
      if (!pos) return;
      const p = project(homography, pos.x, pos.y, imageSize);
      if (!p) return;
      const [x, y] = [p[0] * w, p[1] * h];
      const rx = w * 0.028;
      const ry = rx * 0.38;
      ctx.globalAlpha = pos.alpha;
      if (dim) {
        ctx.fillStyle = "rgba(0,0,0,0.45)";
        ctx.beginPath();
        ctx.rect(0, 0, w, h);
        ctx.ellipse(x, y - rx * 1.6, rx * 2.2, rx * 3.2, 0, 0, Math.PI * 2, true);
        ctx.fill("evenodd");
      }
      if (showTrail) {
        const path = trail(cache.samples, t, 3000)
          .map((s) => project(homography, s.x, s.y, imageSize))
          .filter((q): q is [number, number] => q !== null);
        ctx.strokeStyle = "rgba(250,204,21,0.8)";
        ctx.lineWidth = 3 * devicePixelRatio;
        ctx.setLineDash([6 * devicePixelRatio, 6 * devicePixelRatio]);
        ctx.beginPath();
        path.forEach(([u, v], i) => (i ? ctx.lineTo(u * w, v * h) : ctx.moveTo(u * w, v * h)));
        ctx.stroke();
        ctx.setLineDash([]);
      }
      ctx.strokeStyle = "#facc15";
      ctx.lineWidth = 4 * devicePixelRatio;
      ctx.beginPath();
      ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
      ctx.stroke();
      if (label) {
        ctx.font = `${Math.round(14 * devicePixelRatio)}px system-ui, sans-serif`;
        const tw = ctx.measureText(label).width;
        ctx.fillStyle = "rgba(17,24,39,0.85)";
        ctx.fillRect(x - tw / 2 - 6, y + ry + 4, tw + 12, 20 * devicePixelRatio);
        ctx.fillStyle = "#fff";
        ctx.fillText(label, x - tw / 2, y + ry + 18 * devicePixelRatio);
      }
      ctx.globalAlpha = 1;
    };
    draw();
    return () => cancelAnimationFrame(raf);
  });

  function pick(e: MouseEvent<HTMLCanvasElement>) {
    if (!picking || !onPick) return;
    const r = e.currentTarget.getBoundingClientRect();
    const t = getTime();
    const rows = rowsAt(t);
    onPick(rows ? nearestTrack(rows, t, homography, imageSize, [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height]) : null);
  }

  return (
    <canvas
      ref={canvas}
      onClick={pick}
      className={picking ? "absolute inset-0 size-full cursor-crosshair" : "pointer-events-none absolute inset-0 size-full"}
      aria-hidden
      data-testid="spotlight"
    />
  );
}

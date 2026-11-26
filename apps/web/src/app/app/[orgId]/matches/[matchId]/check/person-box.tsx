"use client";

import { useEffect, useRef } from "react";
import { courtToPicture, ViewChunks, type Geometry } from "@/lib/moving-camera";
import { boxOnCanvas, cropView, personBox, positionAt, trackSamples, type Sample } from "@/lib/spotlight";

const ZOOM = 3.2; // the crop is this many box heights tall

/**
 * The person a question is about, as a crop of the running video with a box around them: the
 * track's foot point projected with the court homography, a fixed body height on top
 * (lib/spotlight.ts personBox). The crop follows the track while the video plays; where the
 * track is lost the full frame shows without a box.
 */
export function PersonCrop({
  baseUrl,
  chunkMs,
  geometry,
  track,
  getTime,
  getVideo,
}: {
  baseUrl: string;
  chunkMs: number;
  /** court -> picture, per frame for a moving camera (lib/moving-camera) */
  geometry: Geometry;
  track: number;
  getTime: () => number;
  getVideo: () => HTMLVideoElement | null;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const chunks = useRef(new Map<number, Sample[] | "loading">());
  useEffect(() => {
    let raf = 0;
    const views = geometry.view ? new ViewChunks(geometry.view.baseUrl, chunkMs) : null;
    const draw = () => {
      raf = requestAnimationFrame(draw);
      const c = canvas.current;
      const v = getVideo();
      if (!c || !v || v.readyState < 2 || !v.videoWidth) return;
      const W = (c.width = c.clientWidth * devicePixelRatio);
      const H = (c.height = c.clientHeight * devicePixelRatio);
      const ctx = c.getContext("2d")!;
      const t = getTime();
      const n = Math.floor(t / chunkMs);
      const hit = chunks.current.get(n);
      if (!hit) {
        chunks.current.set(n, "loading");
        void fetch(`${baseUrl}/${n}`, { credentials: "same-origin" })
          .then((r) => (r.ok ? r.arrayBuffer() : null))
          .then((buf) => (buf ? chunks.current.set(n, trackSamples(new Float32Array(buf), track)) : chunks.current.delete(n)));
      }
      const pos = hit && hit !== "loading" ? positionAt(hit, t) : null;
      // a moving camera: where it looked at this moment; unknown, the full frame without a box
      const place = pos ? courtToPicture(geometry, views, t) : null;
      const box = pos && place ? personBox(place.homography, pos.x, pos.y, place.size) : null;
      const vw = v.videoWidth;
      const vh = v.videoHeight;
      // one scale for both axes, letterboxed: the box stays on the person at every size (L5)
      const view = cropView(box, vw, vh, W, H, ZOOM);
      ctx.fillStyle = "black";
      ctx.fillRect(0, 0, W, H);
      ctx.drawImage(v, view.sx, view.sy, view.sw, view.sh, view.dx, view.dy, view.dw, view.dh);
      if (!box) return;
      const r = boxOnCanvas(box, vw, vh, view);
      ctx.globalAlpha = pos!.alpha;
      ctx.lineWidth = 4 * devicePixelRatio;
      ctx.strokeStyle = getComputedStyle(c).getPropertyValue("--attn").trim() || "yellow";
      ctx.strokeRect(r.x, r.y, r.w, r.h);
      ctx.globalAlpha = 1;
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [baseUrl, chunkMs, geometry, track, getTime, getVideo]);
  return <canvas ref={canvas} aria-hidden className="pointer-events-none absolute inset-0 size-full bg-black" data-testid="person-box" />;
}

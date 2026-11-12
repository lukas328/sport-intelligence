"use client";

import { useEffect, useRef } from "react";
import { personBox, positionAt, trackSamples, type Homography, type Sample } from "@/lib/spotlight";

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
  homography,
  imageSize,
  track,
  getTime,
  getVideo,
}: {
  baseUrl: string;
  chunkMs: number;
  homography: Homography;
  imageSize: [number, number];
  track: number;
  getTime: () => number;
  getVideo: () => HTMLVideoElement | null;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const chunks = useRef(new Map<number, Sample[] | "loading">());
  useEffect(() => {
    let raf = 0;
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
      const box = pos ? personBox(homography, pos.x, pos.y, imageSize) : null;
      const vw = v.videoWidth;
      const vh = v.videoHeight;
      if (!box) {
        ctx.drawImage(v, 0, 0, vw, vh, 0, 0, W, H);
        return;
      }
      // the crop around the box, in the video's own pixels, kept inside the frame
      const bh = box.h * vh;
      const ch = Math.min(vh, Math.max(bh * ZOOM, vh * 0.2));
      const cw = Math.min(vw, (ch * W) / H);
      const cx = Math.min(Math.max((box.x + box.w / 2) * vw - cw / 2, 0), vw - cw);
      const cy = Math.min(Math.max((box.y + box.h / 2) * vh - ch / 2, 0), vh - ch);
      ctx.drawImage(v, cx, cy, cw, ch, 0, 0, W, H);
      const k = W / cw;
      ctx.globalAlpha = pos!.alpha;
      ctx.lineWidth = 4 * devicePixelRatio;
      ctx.strokeStyle = getComputedStyle(c).getPropertyValue("--attn").trim() || "yellow";
      ctx.strokeRect((box.x * vw - cx) * k, (box.y * vh - cy) * k, box.w * vw * k, bh * k);
      ctx.globalAlpha = 1;
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [baseUrl, chunkMs, homography, imageSize, track, getTime, getVideo]);
  return <canvas ref={canvas} aria-hidden className="pointer-events-none absolute inset-0 size-full bg-black" data-testid="person-box" />;
}

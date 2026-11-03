"use client";

import { useEffect, useRef } from "react";

const MAX_DRIFT_S = 0.08; // two frames at 25 fps

/**
 * A second camera that follows the main player (time in that video = main time + offset).
 * Mirrors play/pause and rate and corrects drift above two frames; no reload when it is shown or
 * hidden (addendum 01, 4.5).
 */
export function SyncedCam({ src, offsetMs, main, className, label }: { src: string; offsetMs: number; main: () => HTMLVideoElement | null; className?: string; label: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    let destroy: (() => void) | undefined;
    if (v.canPlayType("application/vnd.apple.mpegurl")) v.src = src;
    else
      void import("hls.js").then(({ default: Hls }) => {
        if (!Hls.isSupported()) return;
        const hls = new Hls({ maxBufferLength: 20, enableWorker: true });
        hls.loadSource(src);
        hls.attachMedia(v);
        destroy = () => hls.destroy();
      });
    return () => destroy?.();
  }, [src]);
  useEffect(() => {
    const id = window.setInterval(() => {
      const m = main();
      const v = ref.current;
      if (!m || !v || v.readyState < 1) return;
      const want = m.currentTime + offsetMs / 1000;
      if (want < 0) return;
      if (Math.abs(v.currentTime - want) > MAX_DRIFT_S) v.currentTime = want;
      if (v.playbackRate !== m.playbackRate) v.playbackRate = m.playbackRate;
      if (m.paused && !v.paused) v.pause();
      if (!m.paused && v.paused) void v.play().catch(() => undefined);
    }, 200);
    return () => window.clearInterval(id);
  }, [main, offsetMs]);
  return <video ref={ref} muted playsInline aria-label={label} className={className} data-testid="synced-cam" />;
}

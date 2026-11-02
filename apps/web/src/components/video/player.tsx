"use client";

import { useTranslations } from "next-intl";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { formatClock, parseThumbVtt, type ThumbCue } from "@/lib/format";
import { cn } from "@/lib/utils";
import { drawShapes, type Shape } from "./shapes";

export interface Marker {
  t_ms: number;
  kind: "comment" | "clip" | "drawing" | "event";
  label?: string;
}

export interface PlayerAnnotation {
  id: string;
  t_ms: number;
  duration_ms: number;
  shapes: Shape[];
}

export interface PlayerHandle {
  seek(ms: number): void;
  play(): void;
  pause(): void;
  time(): number;
  video(): HTMLVideoElement | null;
}

interface Props {
  src: string;
  poster?: string | undefined;
  thumbsVtt?: string | undefined;
  fps?: number | null | undefined;
  markers?: Marker[];
  annotations?: PlayerAnnotation[];
  /** Restrict playback to a window (clip) and call onWindowEnd when it is reached. */
  window?: { start_ms: number; end_ms: number } | undefined;
  onWindowEnd?: () => void;
  onTime?: (ms: number) => void;
  onKey?: (key: string) => boolean; // return true when handled
  overlay?: ReactNode;
  autoPlay?: boolean;
}

const SPEEDS = [0.25, 0.5, 1, 1.5, 2];

export const VideoPlayer = forwardRef<PlayerHandle, Props>(function VideoPlayer(
  { src, poster, thumbsVtt, fps, markers = [], annotations = [], window: win, onWindowEnd, onTime, onKey, overlay, autoPlay },
  ref,
) {
  const t = useTranslations("player");
  const videoRef = useRef<HTMLVideoElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState(false);
  const [thumbs, setThumbs] = useState<ThumbCue[]>([]);
  const [hover, setHover] = useState<{ x: number; t: number } | null>(null);
  const frame = 1 / (fps && fps > 0 ? fps : 25);

  useImperativeHandle(ref, () => ({
    seek: (ms) => {
      if (videoRef.current) videoRef.current.currentTime = ms / 1000;
    },
    play: () => void videoRef.current?.play(),
    pause: () => videoRef.current?.pause(),
    time: () => (videoRef.current?.currentTime ?? 0) * 1000,
    video: () => videoRef.current,
  }));

  // HLS: native in Safari/iOS, hls.js elsewhere (loaded only here to keep other routes light)
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let destroy: (() => void) | undefined;
    setError(false);
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
    } else {
      void import("hls.js").then(({ default: Hls }) => {
        if (!Hls.isSupported()) {
          setError(true);
          return;
        }
        const hls = new Hls({ maxBufferLength: 30, enableWorker: true }); // same origin: cookies are sent
        hls.on(Hls.Events.ERROR, (_e, data) => {
          if (data.fatal) setError(true);
        });
        hls.loadSource(src);
        hls.attachMedia(video);
        destroy = () => hls.destroy();
      });
    }
    return () => destroy?.();
  }, [src]);

  useEffect(() => {
    if (!thumbsVtt) return;
    const base = thumbsVtt.slice(0, thumbsVtt.lastIndexOf("/") + 1);
    void fetch(thumbsVtt, { credentials: "same-origin" })
      .then((r) => (r.ok ? r.text() : ""))
      .then((text) => setThumbs(parseThumbVtt(text, base)));
  }, [thumbsVtt]);

  // clip window: start at its beginning, stop at its end
  useEffect(() => {
    const v = videoRef.current;
    if (v && win) {
      v.currentTime = win.start_ms / 1000;
      if (autoPlay) void v.play().catch(() => undefined);
    }
  }, [win?.start_ms, win?.end_ms, autoPlay]); // eslint-disable-line react-hooks/exhaustive-deps

  // render saved drawings that are active at the current time
  const renderOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    const v = videoRef.current;
    if (!canvas || !v) return;
    const { width, height } = canvas.getBoundingClientRect();
    if (canvas.width !== Math.round(width) || canvas.height !== Math.round(height)) {
      canvas.width = Math.round(width);
      canvas.height = Math.round(height);
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const now = v.currentTime * 1000;
    const active = annotations.filter((a) => now >= a.t_ms && now <= a.t_ms + a.duration_ms);
    for (const a of active) drawShapes(ctx, a.shapes, canvas.width, canvas.height);
  }, [annotations]);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const v = videoRef.current;
      if (v) {
        const ms = v.currentTime * 1000;
        setTime(ms);
        onTime?.(ms);
        if (win && ms >= win.end_ms) {
          v.pause();
          onWindowEnd?.();
        }
      }
      renderOverlay();
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [renderOverlay, onTime, win, onWindowEnd]);

  const seekBy = (s: number) => {
    const v = videoRef.current;
    if (v) v.currentTime = Math.max(0, Math.min(v.duration || Infinity, v.currentTime + s));
  };
  const step = (dir: 1 | -1) => {
    videoRef.current?.pause();
    seekBy(dir * frame);
  };
  const setRate = (r: number) => {
    setSpeed(r);
    if (videoRef.current) videoRef.current.playbackRate = r;
  };
  const toggle = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) void v.play();
    else v.pause();
  };

  function onKeyDown(e: React.KeyboardEvent) {
    if ((e.target as HTMLElement).closest("input, textarea, select")) return;
    if (onKey?.(e.key)) return e.preventDefault();
    const i = SPEEDS.indexOf(speed);
    const actions: Record<string, () => void> = {
      " ": toggle,
      k: toggle,
      ArrowLeft: () => seekBy(-5),
      ArrowRight: () => seekBy(5),
      j: () => seekBy(-10),
      l: () => seekBy(10),
      ",": () => step(-1),
      ".": () => step(1),
      "[": () => setRate(SPEEDS[Math.max(0, i - 1)]!),
      "]": () => setRate(SPEEDS[Math.min(SPEEDS.length - 1, i + 1)]!),
      m: () => setMuted((m) => !m),
      f: () => void (document.fullscreenElement ? document.exitFullscreen() : boxRef.current?.requestFullscreen()),
    };
    const action = actions[e.key];
    if (action) {
      e.preventDefault();
      action();
    }
  }

  const pct = (ms: number) => (duration > 0 ? (ms / (duration * 1000)) * 100 : 0);
  const thumb = hover ? thumbs.find((c) => hover.t >= c.start && hover.t < c.end) : undefined;

  return (
    <div
      ref={boxRef}
      tabIndex={0}
      onKeyDown={onKeyDown}
      className="group relative overflow-hidden rounded-lg bg-black outline-none focus-visible:ring-2 focus-visible:ring-accent"
      aria-label={t("shortcutsList")}
      data-testid="player"
    >
      <div className="relative">
        <video
          ref={videoRef}
          poster={poster}
          muted={muted}
          playsInline
          preload="metadata"
          className="block aspect-video w-full bg-black"
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
          onDurationChange={(e) => setDuration(e.currentTarget.duration)}
          onClick={toggle}
          data-testid="video"
        />
        <canvas ref={canvasRef} aria-hidden className="pointer-events-none absolute inset-0 h-full w-full" />
        {overlay}
        {error && (
          <p role="alert" className="absolute inset-x-0 top-1/2 text-center text-white">
            {t("error")}
          </p>
        )}
      </div>

      <div className="space-y-1 bg-neutral-900 px-3 py-2 text-white">
        <div
          className="relative h-6 cursor-pointer"
          onMouseMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            setHover({ x: e.clientX - r.left, t: ((e.clientX - r.left) / r.width) * duration });
          }}
          onMouseLeave={() => setHover(null)}
        >
          <input
            type="range"
            min={0}
            max={Math.max(duration, 0.01)}
            step={0.01}
            value={time / 1000}
            onChange={(e) => {
              if (videoRef.current) videoRef.current.currentTime = Number(e.target.value);
            }}
            aria-label={t("seek")}
            aria-valuetext={formatClock(time)}
            className="absolute inset-x-0 top-1 w-full accent-[var(--accent)]"
          />
          {win && (
            <div
              aria-hidden
              className="pointer-events-none absolute top-0 h-1 bg-yellow-400"
              style={{ left: `${pct(win.start_ms)}%`, width: `${pct(win.end_ms - win.start_ms)}%` }}
            />
          )}
          {markers.map((m, i) => (
            <span
              key={i}
              aria-hidden
              title={m.label}
              className={cn(
                "pointer-events-none absolute bottom-0 h-2 w-1 -translate-x-1/2 rounded-sm",
                m.kind === "comment" ? "bg-sky-400" : m.kind === "clip" ? "bg-yellow-400" : m.kind === "drawing" ? "bg-pink-400" : "bg-white",
              )}
              style={{ left: `${pct(m.t_ms)}%` }}
            />
          ))}
          {hover && thumb && (
            <div
              aria-hidden
              className="pointer-events-none absolute bottom-7 -translate-x-1/2 overflow-hidden rounded border border-white/40"
              style={{
                left: hover.x,
                width: thumb.w,
                height: thumb.h,
                backgroundImage: `url(${thumb.url})`,
                backgroundPosition: `-${thumb.x}px -${thumb.y}px`,
              }}
            >
              <span className="absolute bottom-0 left-0 bg-black/60 px-1 text-xs">{formatClock(hover.t * 1000)}</span>
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1 text-sm">
          <CtlButton label={playing ? t("pause") : t("play")} onClick={toggle}>
            {playing ? "❚❚" : "▶"}
          </CtlButton>
          <CtlButton label={t("back5")} onClick={() => seekBy(-5)}>
            −5
          </CtlButton>
          <CtlButton label={t("fwd5")} onClick={() => seekBy(5)}>
            +5
          </CtlButton>
          <CtlButton label={t("frameBack")} onClick={() => step(-1)}>
            ⏮
          </CtlButton>
          <CtlButton label={t("frameFwd")} onClick={() => step(1)}>
            ⏭
          </CtlButton>
          <span className="px-2 tabular-nums" data-testid="clock">
            {formatClock(time)} / {formatClock(duration * 1000)}
          </span>
          <span className="flex-1" />
          <label className="flex items-center gap-1">
            <span className="sr-only">{t("speed")}</span>
            <select
              value={speed}
              onChange={(e) => setRate(Number(e.target.value))}
              className="rounded bg-neutral-800 px-1 py-1"
              aria-label={t("speed")}
            >
              {SPEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}×
                </option>
              ))}
            </select>
          </label>
          <CtlButton label={muted ? t("unmute") : t("mute")} onClick={() => setMuted((m) => !m)}>
            {muted ? "🔇" : "🔊"}
          </CtlButton>
          <CtlButton
            label={t("fullscreen")}
            onClick={() => void (document.fullscreenElement ? document.exitFullscreen() : boxRef.current?.requestFullscreen())}
          >
            ⛶
          </CtlButton>
        </div>
      </div>
    </div>
  );
});

function CtlButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="min-h-9 min-w-9 rounded px-2 hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-white"
    >
      <span aria-hidden>{children}</span>
    </button>
  );
}

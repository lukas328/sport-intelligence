"use client";

import { User, X } from "lucide-react";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { FrameGrabber, stillRect } from "@/lib/frame-grabber";
import { courtToPictureAt, type Geometry } from "@/lib/moving-camera";
import { personBox, trackSamples } from "@/lib/spotlight";
import { cn } from "@/lib/utils";
import { VideoPlayer, type PlayerHandle } from "./player";
import { SpotlightOverlay } from "./spotlight";

const Frames = createContext<FrameGrabber | null>(null);

/** One hidden video for all stills of a list (lib/frame-grabber). */
export function FramesProvider({ src, children }: { src: string; children: ReactNode }) {
  const [grabber, setGrabber] = useState<FrameGrabber | null>(null);
  useEffect(() => {
    const g = new FrameGrabber(src);
    setGrabber(g);
    return () => g.destroy();
  }, [src]);
  return <Frames.Provider value={grabber}>{children}</Frames.Provider>;
}

/** A track's sample nearest to `at` within its 30 s file: the moment and the foot point. */
async function footAt(tracksUrl: string, chunkMs: number, track: number, at: number): Promise<{ t: number; x: number; y: number } | null> {
  const r = await fetch(`${tracksUrl}/${Math.floor(at / chunkMs)}`, { credentials: "same-origin" }).catch(() => null);
  if (!r?.ok) return null;
  const samples = trackSamples(new Float32Array(await r.arrayBuffer()), track);
  let best: (typeof samples)[number] | null = null;
  for (const s of samples) if (!best || Math.abs(s.t - at) < Math.abs(best.t - at)) best = s;
  return best && Math.abs(best.t - at) <= 2000 ? best : null;
}

/**
 * A still picture of one person of the analysis: the frame at a moment of their track, cut to
 * the box around their foot point (lib/spotlight personBox; a moving camera through its view
 * files). So the coach sees who is meant while sorting, without going to the video. Shows a
 * figure while it loads or where the person cannot be placed.
 */
export function PersonStill({
  geometry,
  tracksUrl,
  chunkMs,
  track,
  at,
  label,
  className,
}: {
  geometry: Geometry;
  tracksUrl: string; // .../videos/{id}/tracks
  chunkMs: number;
  track: number;
  at: number;
  label: string;
  className?: string;
}) {
  const grabber = useContext(Frames);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [state, setState] = useState<"loading" | "shown" | "none">("loading");
  useEffect(() => {
    if (!grabber) return;
    let live = true;
    let cancel = () => {};
    setState("loading");
    void (async () => {
      const foot = await footAt(tracksUrl, chunkMs, track, at);
      const place = foot ? await courtToPictureAt(geometry, chunkMs, foot.t) : null;
      const box = foot && place ? personBox(place.homography, foot.x, foot.y, place.size) : null;
      if (!live) return;
      if (!foot || !box) return setState("none");
      cancel = grabber.grab(
        foot.t,
        (v) => {
          const c = canvas.current;
          if (!live || !c) return;
          const r = stillRect(box, v.videoWidth, v.videoHeight, c.width / c.height);
          c.getContext("2d")?.drawImage(v, r.sx, r.sy, r.sw, r.sh, 0, 0, c.width, c.height);
          setState("shown");
        },
        () => live && setState("none"),
      );
    })();
    return () => {
      live = false;
      cancel();
    };
  }, [grabber, geometry, tracksUrl, chunkMs, track, at]);
  return (
    <span role="img" aria-label={label} className={cn("relative block shrink-0 overflow-hidden bg-ink/10", className)} data-testid="person-still" data-state={state}>
      <canvas ref={canvas} width={96} height={128} aria-hidden className={cn("block size-full", state !== "shown" && "invisible")} />
      {state !== "shown" && (
        <User aria-hidden className={cn("absolute inset-0 m-auto size-1/2 text-ink-2", state === "loading" && "animate-pulse motion-reduce:animate-none")} />
      )}
    </span>
  );
}

/**
 * One person of the analysis playing in a small player inside the step (sticky on a phone, so it
 * stays in view over a list), with the ring on them where the court is known.
 */
export function InlinePersonPlayer({
  video,
  track,
  geometry,
  chunkMs,
  title,
  closeLabel,
  onClose,
  testId = "person-player",
}: {
  video: string; // /v1/orgs/{org}/videos/{id}
  track: { track_no: number; first_ms: number; last_ms: number };
  geometry: Geometry | null;
  chunkMs: number | null;
  title: string;
  closeLabel: string;
  onClose: () => void;
  testId?: string;
}) {
  const player = useRef<PlayerHandle>(null);
  return (
    <div className="sticky top-0 z-10 bg-paper pb-2" data-testid={testId}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <p className="m-0 min-w-0 truncate text-sm font-semibold">{title}</p>
        <Button variant="quiet" size="sm" className="min-h-11 min-w-11" onClick={onClose} aria-label={closeLabel}>
          <X aria-hidden className="size-4" />
        </Button>
      </div>
      <VideoPlayer
        ref={player}
        key={track.track_no}
        src={`${video}/media/hls/master.m3u8`}
        window={{ start_ms: Math.max(0, track.first_ms - 500), end_ms: Math.min(track.last_ms, track.first_ms + 8000) }}
        autoPlay
        loop
        under
        overlay={
          geometry && chunkMs ? (
            <SpotlightOverlay baseUrl={`${video}/tracks`} chunkMs={chunkMs} geometry={geometry} track={track.track_no} label="" getTime={() => player.current?.time() ?? 0} showTrail={false} />
          ) : undefined
        }
      />
    </div>
  );
}

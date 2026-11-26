"use client";

import { Pipette } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type MouseEvent } from "react";
import { Button } from "@/components/ui/button";
import { meanHex, videoPoint } from "@/lib/pick-colour";

const SAMPLE = 7; // px around the tap

/**
 * The colour of our shirt taken from the video itself, at the upload: the file is in the
 * browser, so a still of it shows right away, before any analysis; a slider moves through it and
 * a tap on a shirt takes its colour for the field players or the goalkeeper. A file the browser
 * cannot show (some phone formats) shows nothing here; the colour fields stay.
 */
export function KitFromVideo({ file, onPick }: { file: File; onPick: (colour: string, which: "own" | "own_gk") => void }) {
  const t = useTranslations("upload");
  const video = useRef<HTMLVideoElement>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [ok, setOk] = useState(true);
  const [duration, setDuration] = useState(0);
  const [at, setAt] = useState(0);
  const [picked, setPicked] = useState<string | null>(null);
  useEffect(() => {
    const u = URL.createObjectURL(file);
    setUrl(u);
    setOk(true);
    setPicked(null);
    return () => URL.revokeObjectURL(u);
  }, [file]);
  if (!url || !ok) return null;
  function onMeta() {
    const v = video.current;
    if (!v || !Number.isFinite(v.duration)) return;
    setDuration(v.duration);
    // a fifth into the file: the warm-up is over, the teams are on the court
    const start = v.duration * 0.2;
    v.currentTime = start;
    setAt(start);
  }
  function pick(e: MouseEvent<HTMLVideoElement>) {
    const v = e.currentTarget;
    const r = v.getBoundingClientRect();
    const p = videoPoint(e.clientX - r.left, e.clientY - r.top, r.width, r.height, v.videoWidth, v.videoHeight);
    if (!p) return;
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;
    ctx.drawImage(v, 0, 0);
    const half = Math.floor(SAMPLE / 2);
    const x = Math.max(0, Math.min(v.videoWidth - SAMPLE, p.x - half));
    const y = Math.max(0, Math.min(v.videoHeight - SAMPLE, p.y - half));
    setPicked(meanHex(ctx.getImageData(x, y, SAMPLE, SAMPLE).data));
  }
  return (
    <div className="mt-4 max-w-[36rem]" data-testid="kit-from-video">
      <p className="m-0 mb-2 flex items-center gap-2 text-[15px] font-semibold">
        <Pipette aria-hidden className="size-4" />
        {t("kitFromVideo")}
      </p>
      <video
        ref={video}
        src={url}
        muted
        playsInline
        preload="metadata"
        onLoadedMetadata={onMeta}
        onError={() => setOk(false)}
        onClick={pick}
        aria-label={t("kitFromVideoStill")}
        className="block aspect-video w-full cursor-crosshair bg-black object-contain"
      />
      {duration > 0 && (
        <input
          type="range"
          min={0}
          max={duration}
          step={0.5}
          value={at}
          aria-label={t("kitFromVideoMoment")}
          onChange={(e) => {
            const s = Number(e.target.value);
            setAt(s);
            if (video.current) video.current.currentTime = s;
          }}
          className="mt-1 block h-11 w-full accent-[var(--accent)]"
        />
      )}
      {picked ? (
        <div className="mt-2 flex flex-wrap items-center gap-2" role="status" data-testid="kit-picked">
          <i aria-hidden className="block size-8 shadow-[0_0_0_1.5px_currentColor]" style={{ background: picked }} />
          <span className="text-[15px]">{t("kitPicked")}</span>
          <Button size="sm" className="max-sm:flex-1" onClick={() => (onPick(picked, "own"), setPicked(null))} data-testid="kit-pick-own">
            {t("kitPickOwn")}
          </Button>
          <Button size="sm" variant="secondary" className="max-sm:flex-1" onClick={() => (onPick(picked, "own_gk"), setPicked(null))} data-testid="kit-pick-gk">
            {t("kitPickGk")}
          </Button>
        </div>
      ) : (
        <p className="m-0 mt-1 text-xs text-muted">{t("kitFromVideoHint")}</p>
      )}
    </div>
  );
}

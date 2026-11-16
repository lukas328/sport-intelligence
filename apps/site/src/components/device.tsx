import type { CSSProperties } from "react";
import { cn } from "@/lib/cn";

/**
 * Frames for the pictures from the app (public/app, scripts/app-screens.mjs). A phone with
 * rounded corners (the only rounded thing on the site: phones are round) and a browser window
 * with square corners and the app's address. Plain markup, no script.
 */
export function Phone({
  src,
  alt,
  width,
  height,
  scroll = false,
  priority = false,
  className,
}: {
  src: string;
  alt: string;
  /** size of the picture in pixels */
  width: number;
  height: number;
  /** a picture taller than the screen runs slowly down and up again (still with reduced motion) */
  scroll?: boolean;
  priority?: boolean;
  className?: string;
}) {
  // the screen shows 390 x 844 CSS pixels of the app; a taller picture scrolls by the rest
  const screen = 844 / 390;
  const visible = Math.min(1, (width * screen) / height);
  const style = { "--scroll-to": `${-((1 - visible) * 100).toFixed(2)}%` } as CSSProperties;
  return (
    <div
      className={cn(
        "phone relative mx-auto w-full max-w-[19rem] bg-ink p-[3.2%] shadow-[0_30px_60px_-20px_rgb(10_13_17/0.45)]",
        className,
      )}
      style={{ borderRadius: "2.6rem" }}
    >
      <div
        className="relative overflow-hidden bg-paper"
        style={{ borderRadius: "2.1rem", aspectRatio: `390 / 844` }}
      >
        <img
          src={src}
          alt={alt}
          width={width}
          height={height}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          fetchPriority={priority ? "high" : undefined}
          className={cn("block h-auto w-full", scroll && "phone-scroll")}
          style={scroll ? style : undefined}
        />
      </div>
    </div>
  );
}

export function Browser({
  src,
  alt,
  width,
  height,
  crop,
  priority = false,
  className,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  /** show only the top of the picture, at this width to height ratio */
  crop?: number;
  priority?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "border-2 border-ink bg-paper shadow-[0_30px_60px_-24px_rgb(10_13_17/0.4)]",
        className,
      )}
    >
      <div aria-hidden className="flex h-7 items-center gap-1.5 bg-ink px-3">
        <i className="size-2 bg-[#5c6168]" style={{ borderRadius: "50%" }} />
        <i className="size-2 bg-[#5c6168]" style={{ borderRadius: "50%" }} />
        <i className="size-2 bg-[#5c6168]" style={{ borderRadius: "50%" }} />
        <span className="ml-3 truncate font-mono text-[0.8125rem] font-medium text-[#aab2ba]">
          app.handball-intelligence.com
        </span>
      </div>
      <div className="overflow-hidden" style={crop ? { aspectRatio: String(crop) } : undefined}>
        <img
          src={src}
          alt={alt}
          width={width}
          height={height}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          fetchPriority={priority ? "high" : undefined}
          className="block h-auto w-full"
        />
      </div>
    </div>
  );
}

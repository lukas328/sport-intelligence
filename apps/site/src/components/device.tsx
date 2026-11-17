import type { CSSProperties } from "react";
import { cn } from "@/lib/cn";

/**
 * The phone frame for a screen of the app that runs slowly down and back (public/product,
 * scripts/product-shots): rounded corners (the only rounded thing on the site: phones are round).
 * Plain markup, no script. The other product pictures carry their frames in the picture.
 */
export function Phone({
  src,
  srcSet,
  sizes,
  alt,
  width,
  height,
  scroll = false,
  priority = false,
  className,
}: {
  src: string;
  /** the same picture at 1x and 2x, with the width it is shown at */
  srcSet?: string;
  sizes?: string;
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
          srcSet={srcSet}
          sizes={sizes}
          alt={alt}
          width={width}
          height={height}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          className={cn("block h-auto w-full", scroll && "phone-scroll")}
          style={scroll ? style : undefined}
        />
      </div>
    </div>
  );
}

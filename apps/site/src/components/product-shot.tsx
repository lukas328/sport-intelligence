import type { ReactNode } from "react";
import { arrow, productShot, type ShotName } from "@/lib/product-shots";
import { cn } from "@/lib/cn";

/**
 * A product picture (public/product, scripts/product-shots) with its callouts: the arrows drawn
 * over the picture and the labels as real text in the visitor's language, so they stay sharp,
 * translatable and readable for screen readers. The picture keeps its size (width and height),
 * so nothing moves while it loads; the arrows draw themselves when the block glides in. On a
 * small picture (under 28rem wide) the labels would cover the app, so arrows and labels go and
 * the words stand in a short list below. Screen readers always read that list, never the labels.
 */
export function ProductShot({
  name,
  alt,
  labels,
  sizes,
  priority = false,
  framed = true,
  caption,
  className,
}: {
  name: ShotName;
  alt: string;
  /** the callout texts by id (messages: product.<name>) */
  labels: Record<string, string>;
  /** how wide the picture is shown, for the browser's choice between 1x and 2x */
  sizes: string;
  priority?: boolean;
  /** an ink frame around the picture, like the site's boxes (not for the transparent hero) */
  framed?: boolean;
  /** a line under the picture */
  caption?: ReactNode;
  className?: string;
}) {
  const shot = productShot(name);
  const callouts = shot.callouts.filter((c) => labels[c.id]);
  return (
    <figure className={cn("shot m-0", className)}>
      <div className={cn("relative", framed && "border-2 border-ink")}>
        <img
          src={shot.src}
          srcSet={shot.srcSet}
          sizes={sizes}
          alt={alt}
          width={shot.width}
          height={shot.height}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          className="block h-auto w-full"
        />
        {callouts.length > 0 && (
          <>
            <svg
              aria-hidden
              viewBox={`0 0 ${shot.width} ${shot.height}`}
              preserveAspectRatio="none"
              className="shot-arrows pointer-events-none absolute inset-0 h-full w-full"
            >
              {callouts.map((c) => {
                const a = arrow(c, shot.width, shot.height);
                return (
                  <g key={c.id}>
                    <path d={a.line} pathLength={1} />
                    <path d={a.head} className="shot-head" />
                  </g>
                );
              })}
            </svg>
            {callouts.map((c) => (
              <span
                key={c.id}
                aria-hidden
                className="shot-label"
                data-place={c.place}
                style={{
                  left: `${c.from[0]}%`,
                  top: `${c.from[1]}%`,
                  maxWidth: `${Math.min(room(c.place, c.from[0]), c.max ?? 46)}%`,
                }}
              >
                {labels[c.id]}
              </span>
            ))}
          </>
        )}
      </div>
      {callouts.length > 0 && (
        // the words once more as a list: read by screen readers, and shown under a small picture,
        // where labels would cover the app (W16: the words below or the labels on it, never both)
        <ul className="shot-legend">
          {callouts.map((c) => (
            <li key={c.id}>{labels[c.id]}</li>
          ))}
        </ul>
      )}
      {caption && <figcaption className="mt-3 text-[1.0625rem]">{caption}</figcaption>}
    </figure>
  );
}

/**
 * How wide a label may grow (per cent of the picture) so that it stays inside it, whatever the
 * language: from its point to the edge it runs towards, at most a little under half the picture.
 */
function room(place: string, x: number): number {
  const right = 100 - x - 1;
  const left = x - 1;
  const w =
    place === "l" || place === "tr" || place === "br"
      ? left
      : place === "t" || place === "b"
        ? 2 * Math.min(left, right)
        : right;
  return Math.max(20, Math.min(46, +w.toFixed(1)));
}

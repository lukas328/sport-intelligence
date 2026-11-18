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
  lettering,
  edge = false,
  phone,
  phoneSizes = "calc(100vw - 2rem)",
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
  /**
   * the word over the match video («Dein Spiel», L8), written by the website in the visitor's
   * language where the picture says (product-shots.json); part of the picture for screen readers
   */
  lettering?: string;
  /**
   * the labels half over the picture's left or right edge (whichever is nearer), so the picture
   * keeps its air (BEFUNDE-2 L13); the place around the picture must leave them room
   */
  edge?: boolean;
  /**
   * another picture for phones (under 40rem), cut for their width (U22): the browser takes it
   * instead of `name`; the callouts are the main picture's, so give it only where there are none
   */
  phone?: ShotName;
  /** how wide the phone picture is shown */
  phoneSizes?: string;
  className?: string;
}) {
  const shot = productShot(name);
  const small = phone ? productShot(phone) : null;
  // at the edge, each label moves out to the nearer side at its height; its arrow starts there
  const callouts = shot.callouts.filter((c) => labels[c.id]).map((c) => (edge ? { ...c, from: [c.from[0] < 50 ? 0 : 100, c.from[1]] as [number, number], place: "edge" as const } : c));
  if (edge) spread(callouts, (24 / shot.height) * 100 + 9);
  const img = (
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
  );
  return (
    <figure className={cn("shot m-0", className)}>
      <div className={cn("relative [container-type:inline-size]", framed && "border-2 border-ink")}>
        {small ? (
          // art direction: the phone picture under 40rem, each with its own size, so nothing moves
          <picture>
            <source media={PHONE_MEDIA} srcSet={small.srcSet} sizes={phoneSizes} width={small.width} height={small.height} />
            {img}
          </picture>
        ) : (
          img
        )}
        {lettering && shot.lettering && (
          <Lettering box={shot.lettering} className={small ? "max-sm:hidden" : undefined}>
            {lettering}
          </Lettering>
        )}
        {lettering && small?.lettering && (
          <Lettering box={small.lettering} className="sm:hidden">
            {lettering}
          </Lettering>
        )}
        {callouts.length > 0 && (
          <>
            <svg
              aria-hidden
              viewBox={`0 0 ${shot.width} ${shot.height}`}
              preserveAspectRatio="none"
              className="shot-arrows pointer-events-none absolute inset-0 h-full w-full"
            >
              {callouts.map((c) => {
                const a = arrow({ ...c, place: "r" }, shot.width, shot.height);
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
                  maxWidth: c.place === "edge" ? "11rem" : `${Math.min(room(c.place, c.from[0]), c.max ?? 46)}%`,
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

/** where the phone picture takes over: under the site's `sm` (40rem), as in the classes above */
const PHONE_MEDIA = "(max-width: 39.99rem)";

/** the word over the match video, in a box of the picture ([x, y, w, h] in per cent) */
function Lettering({ box, className, children }: { box: [number, number, number, number]; className?: string; children: ReactNode }) {
  return (
    <span
      aria-hidden
      className={cn(
        "pointer-events-none absolute grid place-items-center text-center font-slant leading-none text-white [text-shadow:0_.04em_.3em_rgb(0_0_0/.45)]",
        className,
      )}
      style={{
        left: `${box[0]}%`,
        top: `${box[1]}%`,
        width: `${box[2]}%`,
        height: `${box[3]}%`,
        fontSize: `${(box[2] * 0.11).toFixed(2)}cqw`,
      }}
    >
      {children}
    </span>
  );
}

/**
 * Labels on the same edge never on top of each other: from the top down, each at least `gap`
 * (per cent of the picture's height) under the one before; moved up again if the last runs out.
 */
function spread(cs: { from: [number, number] }[], gap: number) {
  for (const side of [0, 100]) {
    const on = cs.filter((c) => c.from[0] === side).sort((a, b) => a.from[1] - b.from[1]);
    for (let i = 1; i < on.length; i++) {
      const prev = on[i - 1]!.from[1];
      if (on[i]!.from[1] - prev < gap) on[i]!.from = [side, prev + gap];
    }
    const last = on[on.length - 1];
    const over = last ? last.from[1] - 94 : 0;
    if (over > 0) for (const c of on) c.from = [side, c.from[1] - over];
  }
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

import { cn } from "@/lib/cn";

/**
 * Photos from real halls (BEFUNDE-4 U48): they carry the feeling of the match, the components
 * carry the explanation, so a photo never stands where the text points at the product. Free stock
 * (Unsplash, Pexels licence), chosen so that no one is shown as recommending us: no names on
 * shirts, no club or sponsor in focus. They are mood, so empty alt and hidden from screen readers, and
 * left out of print. Files in public/media, made by scripts/photos.py.
 */
const PHOTOS = {
  /** the ball in front of an empty goal: the evening after the match */
  "tor-ball": { widths: [900, 1400, 2000], width: 2000, height: 1331 },
  /** a jump shot over the block, cut to the thrower */
  sprungwurf: { widths: [600, 900, 1300], width: 1300, height: 1100 },
} as const;

export type PhotoName = keyof typeof PHOTOS;

export function HallPhoto({
  name,
  sizes,
  tint,
  className,
  imgClassName,
}: {
  name: PhotoName;
  sizes: string;
  /** in the shirt colour (the visitor's pick in the header): grey picture over the club colour */
  tint?: boolean;
  className?: string;
  imgClassName?: string;
}) {
  const p = PHOTOS[name];
  const src = (w: number) => `/media/${name}-${w}.webp`;
  return (
    <div
      aria-hidden
      className={cn("relative overflow-hidden print:hidden", tint && "bg-club", className)}
    >
      <img
        src={src(p.widths[1])}
        srcSet={p.widths.map((w) => `${src(w)} ${w}w`).join(", ")}
        sizes={sizes}
        alt=""
        width={p.width}
        height={p.height}
        loading="lazy"
        decoding="async"
        className={cn(
          "block size-full object-cover",
          tint && "mix-blend-luminosity contrast-[1.08] grayscale",
          imgClassName,
        )}
      />
    </div>
  );
}

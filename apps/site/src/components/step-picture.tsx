import { ProductShot } from "@/components/product-shot";
import { cn } from "@/lib/cn";
import type { Locale } from "@/lib/i18n";
import type { ShotName } from "@/lib/product-shots";

/**
 * The pictures of the four steps of «So funktioniert es» (U33, after Lukas' design): 1 where the
 * camera goes (the court from above, its light over both goals, «3m»), 2 the match chosen and the
 * upload running («12 %»), 3 «Passt das Spielfeld?» with the proposed field, 4 «11 von 29» with
 * the shot spots and the collection for the team chat. Each in the same square frame on the dark
 * court ground, with words in the picture, so one file per language
 * (scripts/product-shots, templates/step-*.html, public/product/step-*-<locale>.webp).
 */
export const STEP_PICTURES = ["step-film", "step-upload", "step-check", "step-result"] as const;

/** the file of a step picture in the visitor's language */
export function stepShot(step: number, locale: Locale): ShotName | null {
  const name = STEP_PICTURES[step];
  return name ? (`${name}-${locale}` as ShotName) : null;
}

/**
 * `large` (default) fills its column up to 26rem, so the words in the picture read on a phone;
 * `small` stays at most 18rem wide, for a short list of the steps.
 */
export function StepPicture({
  step,
  locale,
  alt,
  size = "large",
  className,
}: {
  /** 0 to 3 */
  step: number;
  locale: Locale;
  alt: string;
  size?: "large" | "small";
  className?: string;
}) {
  const name = stepShot(step, locale);
  if (!name) return null;
  return (
    <ProductShot
      name={name}
      alt={alt}
      labels={{}}
      sizes={size === "small" ? "min(18rem, calc(100vw - 2rem))" : "(min-width: 768px) 26rem, calc(100vw - 2rem)"}
      className={cn(size === "small" && "w-full max-w-[18rem]", className)}
    />
  );
}

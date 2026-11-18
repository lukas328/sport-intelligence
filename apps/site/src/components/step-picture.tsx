import { ProductShot } from "@/components/product-shot";
import { cn } from "@/lib/cn";

/**
 * The pictures of the four steps (U1, U3), one set for the start page and «So funktioniert es»:
 * 1 where the camera goes (a drawing of the hall), 2 choosing the match and the upload running,
 * 3 «Passt das Spielfeld?» with the proposed field, 4 the first of the three things. Each one
 * moment, large, in the same square frame (scripts/product-shots, templates/step-*.html).
 */
export const STEP_PICTURES = ["step-film", "step-upload", "step-check", "step-result"] as const;

/**
 * `large` (default) fills its column up to 26rem, so the app's words read on a phone; `small`
 * stays at most 18rem wide, for a short list of the steps (start page).
 */
export function StepPicture({
  step,
  alt,
  size = "large",
  className,
}: {
  /** 0 to 3 */
  step: number;
  alt: string;
  size?: "large" | "small";
  className?: string;
}) {
  const name = STEP_PICTURES[step];
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

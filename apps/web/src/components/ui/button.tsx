import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "quiet";
export type ButtonSize = "sm" | "md" | "lg" | "icon" | "icon-sm";

// Anlauf: buttons are ink. Filled for the one action, outlined for the others; no radius, no shadow.
const VARIANTS: Record<ButtonVariant, string> = {
  primary: "border-2 border-ink bg-ink text-ground hover:bg-ink/85 disabled:border-rule disabled:bg-rule disabled:text-ink-2 disabled:opacity-100 aria-disabled:border-rule aria-disabled:bg-rule aria-disabled:text-ink-2 aria-disabled:opacity-100",
  secondary: "border-2 border-ink bg-transparent text-ink hover:bg-ink/5",
  ghost: "text-ink hover:bg-ink/5",
  quiet: "text-ink-2 hover:bg-ink/5 hover:text-ink",
  danger: "border-2 border-loss bg-loss text-white hover:brightness-95",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "min-h-11 gap-2 px-3.5 text-[15px]",
  md: "min-h-12 gap-2.5 px-5 text-base",
  lg: "min-h-14 gap-2.5 px-6 text-[17px]",
  icon: "size-11 shrink-0",
  "icon-sm": "size-11 shrink-0",
};

/** Class names of a button, for links that look like one. */
export function buttonClass(variant: ButtonVariant = "primary", size: ButtonSize = "md", className?: string): string {
  return cn(
    "inline-flex cursor-pointer select-none items-center justify-center whitespace-nowrap font-bold no-underline transition-[background,filter,color] duration-150",
    "focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink",
    "disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50",
    "[&_svg]:size-[18px] [&_svg]:shrink-0",
    VARIANTS[variant],
    SIZES[size],
    className,
  );
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "primary", size = "md", loading, disabled, children, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass(variant, size, className)}
      {...props}
    >
      {loading && <span aria-hidden className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {children}
    </button>
  );
});

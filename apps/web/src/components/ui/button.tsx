import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "quiet";
export type ButtonSize = "sm" | "md" | "lg" | "icon" | "icon-sm";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-contrast hover:brightness-[0.92] active:brightness-90",
  secondary: "bg-raised text-foreground ring-1 ring-inset ring-foreground/20 hover:ring-foreground/40 hover:bg-surface",
  ghost: "text-foreground hover:bg-surface",
  quiet: "text-muted hover:bg-surface hover:text-foreground",
  danger: "bg-error text-white hover:brightness-95",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "min-h-8 gap-1.5 px-3 text-[0.8125rem]",
  md: "min-h-10 gap-2 px-4 text-[0.9375rem]",
  lg: "min-h-12 gap-2 px-6 text-base",
  icon: "size-10 shrink-0",
  "icon-sm": "size-8 shrink-0",
};

/** Class names of a button, for links that look like one. */
export function buttonClass(variant: ButtonVariant = "primary", size: ButtonSize = "md", className?: string): string {
  return cn(
    "inline-flex select-none items-center justify-center whitespace-nowrap rounded-md font-semibold transition-[background,filter,color,box-shadow] duration-150",
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
    "disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50",
    "[&_svg]:size-4 [&_svg]:shrink-0",
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

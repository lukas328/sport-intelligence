import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type Tone = "neutral" | "accent" | "ok" | "error" | "warn";

const TONES: Record<Tone, string> = {
  neutral: "bg-surface text-muted",
  accent: "bg-accent/12 text-accent",
  ok: "bg-ok/12 text-ok",
  error: "bg-error/12 text-error",
  warn: "bg-warn/12 text-warn",
};

export function Badge({ tone = "neutral", children, className, ...rest }: { tone?: Tone; children: ReactNode; className?: string; "data-testid"?: string }) {
  return (
    <span
      className={cn("inline-flex items-center gap-1 whitespace-nowrap px-2 py-0.5 text-xs font-semibold [&_svg]:size-3", TONES[tone], className)}
      {...rest}
    >
      {children}
    </span>
  );
}

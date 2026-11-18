import { cn } from "@/lib/cn";

/** The handball: yellow, an ink edge and its seams (the steps of «So funktioniert es»). */
export function BallIcon({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="-20 -20 40 40" className={cn("block h-full w-full overflow-visible", className)}>
      <circle r={17} fill="var(--attn)" stroke="var(--ink)" strokeWidth={3} />
      <path d="M-15 -5C-5 -1 5 -9 13 -9M-6 15C-2 6 7 3 16 5M-3 -16C-9 -6 -9 6 -6 15" fill="none" stroke="var(--ink)" strokeWidth={2.4} />
    </svg>
  );
}

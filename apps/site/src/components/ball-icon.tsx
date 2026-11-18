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

/** The running ball of components/ball-run.tsx, centred on its (size-0) parent, with a hard shadow. */
export function RunBall() {
  return (
    <span className="absolute -top-[1.25rem] -left-[1.25rem] block size-[2.5rem] drop-shadow-[3px_3px_0_var(--ink)]">
      <BallIcon />
    </span>
  );
}

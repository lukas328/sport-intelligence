import { cn } from "@/lib/utils";

/** Product mark: the goal area seen from above (6 m arc in front of the goal). Working title, Q-PROD-1. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn("size-8", className)}>
      <rect width="32" height="32" rx="9" fill="currentColor" />
      <path d="M7 9.5h18" stroke="var(--background)" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M8 9.5c0 8 3.6 13 8 13s8-5 8-13" fill="none" stroke="var(--background)" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="16" cy="15" r="2.4" fill="var(--accent)" />
    </svg>
  );
}

export function BrandWordmark({ name, className }: { name: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <BrandMark className="size-7" />
      <span className="text-[1.0625rem] font-bold tracking-tight font-wide">{name}</span>
    </span>
  );
}

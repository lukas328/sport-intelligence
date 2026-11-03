"use client";

import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface TabItem<T extends string> {
  value: T;
  label: ReactNode;
  testId?: string;
}

/**
 * Segmented control with the ARIA tab pattern (arrow keys move and select). Use for switching
 * views of the same thing; use links for navigation between pages.
 */
export function Segmented<T extends string>({
  items,
  value,
  onChange,
  label,
  size = "md",
  className,
  idPrefix,
}: {
  items: TabItem<T>[];
  value: T;
  onChange: (v: T) => void;
  label: string;
  size?: "sm" | "md";
  className?: string;
  idPrefix?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  function onKey(e: KeyboardEvent, i: number) {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    const to = e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : d ? (i + d + items.length) % items.length : -1;
    if (to < 0) return;
    e.preventDefault();
    refs.current[to]?.focus();
    onChange(items[to]!.value);
  }
  return (
    <div className={cn("scrollbar-none -mx-1 overflow-x-auto px-1", className)}>
      <div role="tablist" aria-label={label} className="inline-flex gap-0.5 rounded-full bg-surface p-1">
        {items.map((it, i) => {
          const active = it.value === value;
          return (
            <button
              key={it.value}
              ref={(el) => {
                refs.current[i] = el;
              }}
              id={idPrefix ? `${idPrefix}-${it.value}` : undefined}
              type="button"
              role="tab"
              aria-selected={active}
              tabIndex={active ? 0 : -1}
              data-testid={it.testId}
              onKeyDown={(e) => onKey(e, i)}
              onClick={() => onChange(it.value)}
              className={cn(
                "whitespace-nowrap rounded-full font-medium transition-[background,color,box-shadow] duration-150",
                size === "sm" ? "px-3 py-1 text-[0.8125rem]" : "px-4 py-1.5 text-sm",
                active ? "bg-raised text-foreground shadow-sm ring-1 ring-border/60" : "text-muted hover:text-foreground",
              )}
            >
              {it.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

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
  variant = "segmented",
  className,
  idPrefix,
}: {
  items: TabItem<T>[];
  value: T;
  onChange: (v: T) => void;
  label: string;
  size?: "sm" | "md";
  /** segmented: a pill group; underline: the main switch of a page, in display type */
  variant?: "segmented" | "underline";
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
    <div
      className={cn(
        "scrollbar-none -mx-1 overflow-x-auto px-1",
        // phones: a fade at the right edge says the row scrolls
        variant === "underline" && size === "sm" && "max-sm:[mask-image:linear-gradient(to_right,black_82%,transparent)]",
        className,
      )}
    >
      <div role="tablist" aria-label={label} className={variant === "underline" ? (size === "sm" ? "inline-flex gap-5" : "inline-flex gap-7") : "inline-flex gap-0.5 rounded-md bg-surface p-1"}>
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
              className={
                variant === "underline"
                  ? cn(
                      "whitespace-nowrap transition-[color,box-shadow] duration-150",
                      // the second level is smaller and underlined in ink, so the main switch stays the main one
                      size === "sm"
                        ? cn("pb-1.5 text-[0.9375rem] font-semibold", active ? "text-foreground shadow-[inset_0_-3px_0_var(--foreground)]" : "text-muted hover:text-foreground")
                        : cn(
                            "pt-1 pb-2 font-display text-xl uppercase tracking-wide",
                            active ? "text-foreground shadow-[inset_0_-4px_0_var(--accent)]" : "text-muted hover:text-foreground hover:shadow-[inset_0_-4px_0_var(--border)]",
                          ),
                    )
                  : cn(
                      "whitespace-nowrap rounded-[5px] font-semibold transition-[background,color] duration-150",
                      size === "sm" ? "px-3 py-1 text-[0.8125rem]" : "px-4 py-1.5 text-sm",
                      active ? "bg-foreground text-background" : "text-muted hover:bg-surface hover:text-foreground",
                    )
              }
            >
              {it.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

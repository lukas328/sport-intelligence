"use client";

import { Check } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, type KeyboardEvent } from "react";
import type { Step, StepId } from "@/lib/match-workflow";
import { cn } from "@/lib/utils";

/** What the side of the video workspace shows: a work step or one of the tools. */
export type Pane = StepId | "events" | "formations" | "notes";

/** The order of work on a match video as one row of tabs: numbered steps with what is still open,
 * then the tools (events, defence systems, notes). One tab is open; the panel sits next to the
 * player, so working through a list never scrolls the video away. */
export function WorkRail({
  steps,
  tools,
  value,
  onChange,
  idPrefix,
}: {
  steps: Step[];
  tools: Pane[];
  value: Pane;
  onChange: (p: Pane) => void;
  idPrefix: string;
}) {
  const t = useTranslations("workflow");
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const all: Pane[] = [...steps.map((s) => s.id), ...tools];
  // the one thing on screen that asks for attention: the first open step
  const signal = steps.find((s) => s.state === "open")?.id;
  function onKey(e: KeyboardEvent, i: number) {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    const to = e.key === "Home" ? 0 : e.key === "End" ? all.length - 1 : d ? (i + d + all.length) % all.length : -1;
    if (to < 0) return;
    e.preventDefault();
    refs.current[to]?.focus();
    onChange(all[to]!);
  }
  const tab = (p: Pane, i: number, body: React.ReactNode, label: string) => (
    <button
      key={p}
      ref={(el) => {
        refs.current[i] = el;
      }}
      type="button"
      role="tab"
      id={`${idPrefix}-tab-${p}`}
      aria-controls={`${idPrefix}-pane`}
      aria-selected={value === p}
      aria-label={label}
      tabIndex={value === p ? 0 : -1}
      onKeyDown={(e) => onKey(e, i)}
      onClick={() => onChange(p)}
      data-testid={`step-${p}`}
      className={cn(
        "-mb-px flex min-h-14 shrink-0 items-center gap-2.5 border-b-[3px] px-2 pb-2 pt-2.5 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset",
        value === p ? "border-foreground text-foreground" : "border-transparent text-muted hover:text-foreground",
      )}
    >
      {body}
    </button>
  );
  return (
    <div className="scrollbar-none -mx-1 overflow-x-auto px-1">
      <div role="tablist" aria-label={t("rail")} className="flex min-w-max items-stretch gap-1 border-b border-foreground/15 sm:gap-3">
        {steps.map((s, i) => {
          const sub = t(`${s.id}_${s.state === "open" ? (s.reason ?? "open") : s.state}`, { n: s.count ?? 0 });
          return tab(
            s.id,
            i,
            <>
              <span
                aria-hidden
                className={cn(
                  "grid size-6 shrink-0 place-items-center rounded-full text-xs font-bold",
                  s.state === "done" ? "bg-surface text-ok" : value === s.id ? "bg-foreground text-background" : "ring-[1.5px] ring-inset ring-current",
                )}
              >
                {s.state === "done" ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
              </span>
              <span className="flex flex-col">
                <span className="font-semibold text-foreground">{t(s.id)}</span>
                <span className={cn("text-[0.8125rem]", s.id === signal ? "self-start rounded-xs bg-signal px-1 font-semibold text-signal-ink" : "text-muted")}>
                  {sub}
                </span>
              </span>
            </>,
            `${t(s.id)}: ${sub}`,
          );
        })}
        {tools.length > 0 && steps.length > 0 && <span aria-hidden className="my-3 w-px shrink-0 bg-foreground/15" />}
        {tools.map((p, j) => tab(p, steps.length + j, <span className="font-semibold">{t(p)}</span>, t(p)))}
      </div>
    </div>
  );
}

"use client";

import { useId, useRef, useState, type ReactNode } from "react";
import { useEscape } from "@/lib/use-escape";

/**
 * A word of the app explained where it first appears on a page (finding A17: «Wurfort»,
 * «Sammlung», «Analyseminuten» stood without an introduction): the word dotted underlined, a tap
 * opens one or two sentences under it, a second tap or Escape closes them.
 */
export function Term({ children, explain, className }: { children: ReactNode; explain: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const box = useRef<HTMLSpanElement>(null);
  useEscape(open, () => setOpen(false), box);
  return (
    <span ref={box} className={`relative inline-block ${className ?? ""}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={id}
        className="cursor-help border-0 bg-transparent p-0 font-[inherit] text-[inherit] underline decoration-dotted decoration-[1.5px] underline-offset-4"
        data-testid="term"
      >
        {children}
      </button>
      {open && (
        <span id={id} role="note" className="absolute top-full left-0 z-20 mt-1.5 block w-max max-w-[min(20rem,80vw)] bg-paper px-3 py-2 text-left font-sans text-[15px] leading-snug font-normal text-ink not-italic ring-2 ring-ink" data-testid="term-text">
          {explain}
        </span>
      )}
    </span>
  );
}

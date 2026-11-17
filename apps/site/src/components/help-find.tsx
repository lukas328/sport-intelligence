"use client";

import { type ReactNode, useEffect, useId, useSyncExternalStore } from "react";
import { matchesAll } from "@/lib/search";

/*
 * The search on «Fragen» (BEFUNDE-3 U8, U9): one field in the page head filters the questions
 * and the guides below it. Everything is in the page as rendered; the field only hides what does
 * not match (with the `hidden` attribute), so without JavaScript the whole page simply stands.
 */

let current = "";
const listeners = new Set<() => void>();
function setQuery(q: string) {
  current = q;
  for (const l of listeners) l();
}
function subscribe(l: () => void) {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}
function useQuery() {
  return useSyncExternalStore(
    subscribe,
    () => current,
    () => "",
  );
}

/** The field in the head, with the number of hits read out as you type. */
export function FindField({ label, hint, texts, hits, hitsOne }: { label: string; hint: string; texts: string[]; hits: string; hitsOne: string }) {
  const query = useQuery();
  const id = useId();
  // a new visit to the page starts with an empty field
  useEffect(() => () => setQuery(""), []);
  const count = texts.filter((t) => matchesAll(t, query)).length;
  return (
    <form role="search" onSubmit={(e) => e.preventDefault()} className="border-2 border-ink bg-paper p-4 shadow-[6px_6px_0_var(--ink)] md:p-5">
      <label htmlFor={id} className="block text-[1.1875rem] font-bold">
        {label}
      </label>
      <div className="relative mt-3">
        <svg viewBox="0 0 24 24" aria-hidden className="pointer-events-none absolute top-1/2 left-4 size-6 -translate-y-1/2">
          <circle cx="10" cy="10" r="6.5" fill="none" stroke="var(--ink)" strokeWidth={2.5} />
          <path d="m15 15 6 6" stroke="var(--ink)" strokeWidth={2.5} />
        </svg>
        <input
          id={id}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-describedby={`${id}-hint`}
          className="min-h-14 w-full border-2 border-ink bg-ground pr-3 pl-13 text-[1.1875rem]"
        />
      </div>
      <p id={`${id}-hint`} className="mt-2 text-base text-ink-2" aria-live="polite">
        {query.trim() ? (count === 1 ? hitsOne : hits.replace("{count}", String(count))) : hint}
      </p>
    </form>
  );
}

/** One question or guide: hidden while the search does not match its text. */
export function Findable({ text, className, children }: { text: string; className?: string; children: ReactNode }) {
  const query = useQuery();
  return (
    <li className={className} hidden={!matchesAll(text, query)}>
      {children}
    </li>
  );
}

/** A group of questions or guides: hidden while none of its texts match. */
export function FindGroup({ texts, className, labelledBy, children }: { texts: string[]; className?: string; labelledBy?: string; children: ReactNode }) {
  const query = useQuery();
  return (
    <section aria-labelledby={labelledBy} className={className} hidden={!texts.some((t) => matchesAll(t, query))}>
      {children}
    </section>
  );
}

/** What stands when nothing matches. */
export function FindNone({ texts, className, children }: { texts: string[]; className?: string; children: ReactNode }) {
  const query = useQuery();
  if (!query.trim() || texts.some((t) => matchesAll(t, query))) return null;
  return <div className={className}>{children}</div>;
}

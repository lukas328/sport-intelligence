import type { ReactNode } from "react";

/** Questions to open one by one: the whole row is the target, a plus or minus as a word-free hint. */
export function Faq({ items }: { items: { q: string; a: ReactNode }[] }) {
  return (
    <div className="border-t-2 border-ink">
      {items.map((f) => (
        <details key={f.q} className="group border-b border-rule">
          <summary className="flex min-h-16 items-center justify-between gap-4 py-3 text-[1.25rem] font-bold md:text-[1.375rem]">
            <span>{f.q}</span>
            <svg viewBox="0 0 24 24" aria-hidden className="size-6 shrink-0">
              <path d="M4 12h16" stroke="var(--ink)" strokeWidth={3} />
              <path d="M12 4v16" stroke="var(--ink)" strokeWidth={3} className="group-open:hidden" />
            </svg>
          </summary>
          <div className="measure pb-6">{f.a}</div>
        </details>
      ))}
    </div>
  );
}

import type { Messages } from "@/messages/de";

/** «Das kann es, das noch nicht»: openly on the page, not in the small print. */
export function Honest({ t, short = false }: { t: Messages["honest"]; short?: boolean }) {
  const can = short ? t.can.slice(0, 3) : t.can;
  const not = short ? t.not.slice(0, 3) : t.not;
  return (
    <div className="grid grid-cols-1 gap-10 md:grid-cols-2 md:gap-12">
      <div>
        <h3 className="font-slant flex items-center gap-3 text-[1.5rem] md:text-[1.75rem]">
          <svg viewBox="0 0 24 24" aria-hidden className="size-7 shrink-0">
            <path d="M4 12.5l5 5L20 6.5" fill="none" stroke="var(--win)" strokeWidth={3} />
          </svg>
          {t.canTitle}
        </h3>
        <ul className="mt-3 border-t-2 border-ink">
          {can.map((x) => (
            <li key={x} className="border-b border-rule py-4">
              {x}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h3 className="font-slant flex items-center gap-3 text-[1.5rem] md:text-[1.75rem]">
          <svg viewBox="0 0 24 24" aria-hidden className="size-7 shrink-0">
            <path d="M5 12h14" fill="none" stroke="var(--ink)" strokeWidth={3} strokeDasharray="4 3" />
          </svg>
          {t.notTitle}
        </h3>
        <ul className="mt-3 border-t-2 border-ink">
          {not.map((x) => (
            <li key={x} className="border-b border-rule py-4">
              {x}
            </li>
          ))}
        </ul>
      </div>
      <p className="text-[1.0625rem] text-ink-2 md:col-span-2">{t.note}</p>
    </div>
  );
}

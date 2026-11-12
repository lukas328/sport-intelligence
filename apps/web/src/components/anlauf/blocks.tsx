import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Section head: slanted title, firm rule, small text or a link at the right. */
export function SectionHead({ title, note, action, as: Tag = "h2", className }: { title: ReactNode; note?: ReactNode; action?: ReactNode; as?: "h2" | "h3"; className?: string }) {
  return (
    <div className={cn("mb-3.5 flex flex-wrap items-baseline gap-3.5 border-b-2 border-ink pb-2.5", className)}>
      <Tag className="font-slant text-[22px] leading-none md:text-[26px]">{title}</Tag>
      {note && <span className="text-[15px] text-ink-2">{note}</span>}
      {action && <span className="ml-auto text-[15px]">{action}</span>}
    </div>
  );
}

/**
 * «Schau hier»: the yellow tag. Only for what needs a look (Prüfen, a marked phase, the running
 * scene), always with a word: `children` is required.
 */
export function AttnTag({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("whitespace-nowrap bg-attn px-2 py-[3px] text-[13px] font-extrabold text-attn-ink", className)}>{children}</span>;
}

/** Legend of line styles: measured and confirmed solid, estimated dashed. */
export function LineKey({ items, className }: { items: { label: ReactNode; estimated?: boolean; color?: string }[]; className?: string }) {
  return (
    <p className={cn("flex flex-wrap items-center gap-3 text-[13px] text-ink-2", className)}>
      {items.map((it, i) => (
        <span key={i}>
          <i
            aria-hidden
            className={cn("mr-1.5 inline-block w-[22px] border-t-[3px] align-middle", it.estimated ? "border-dashed opacity-60" : "border-solid")}
            style={{ borderColor: it.color ?? "var(--ink)" }}
          />
          {it.label}
        </span>
      ))}
    </p>
  );
}

/** Legend of the tactics camera: us, them, referee, ball. */
export function CameraKey({ us, them, referee, ball }: { us: ReactNode; them: ReactNode; referee?: ReactNode; ball?: ReactNode }) {
  return (
    <p className="mt-2 flex flex-wrap items-center gap-3.5 text-[13px] text-ink-2">
      <span>
        <i aria-hidden className="mr-1.5 inline-block size-3 rounded-full bg-club-cam align-[-1px] shadow-[0_0_0_1px_var(--ink)]" />
        {us}
      </span>
      <span>
        <i aria-hidden className="mr-1.5 inline-block size-3 rounded-full bg-opp-cam align-[-1px] shadow-[inset_0_0_0_2.5px_var(--opp-cam-edge),0_0_0_1px_var(--ink)]" />
        {them}
      </span>
      {referee && (
        <span>
          <i aria-hidden className="mr-1.5 inline-block size-3 rotate-45 scale-80 bg-court-ref align-[-1px]" />
          {referee}
        </span>
      )}
      {ball && (
        <span>
          <i aria-hidden className="mr-1.5 inline-block size-2.5 rounded-full bg-white align-[-1px] shadow-[0_0_0_1.5px_var(--ink)]" />
          {ball}
        </span>
      )}
    </p>
  );
}

/** The active marker: a short slanted band in the club colour under the current place. */
export function ActiveMark({ className }: { className?: string }) {
  return <span aria-hidden data-mark="" className={cn("mark-band pointer-events-none absolute h-1.5", className)} />;
}

/** The own row in a table (the league table): a small slanted chip in the club colour. */
export function OwnRowMark() {
  return <span aria-hidden data-mark="" className="mr-2 inline-block h-3 w-3.5 -skew-x-12 bg-club align-middle shadow-[inset_0_0_0_1px_var(--club-edge)]" />;
}

/** Inline text link: ink, underlined. */
export const linkClass = "font-bold text-ink underline decoration-[1.5px] underline-offset-4";

/**
 * Tabs as links (second level of a destination, tabs of a match): slanted, a firm rule under the
 * row, the active tab with the club band. `extra` sits at the right (e.g. Prüfen with a count).
 */
export function LinkTabs({
  label,
  items,
  active,
  extra,
  className,
}: {
  label: string;
  items: { key: string; href: string; label: ReactNode; testId?: string }[];
  active: string | null;
  extra?: ReactNode;
  className?: string;
}) {
  return (
    <nav aria-label={label} className={cn("scrollbar-none flex overflow-x-auto border-b-2 border-ink", className)}>
      {items.map((it) => {
        const on = it.key === active;
        return (
          <Link
            key={it.key}
            href={it.href}
            data-testid={it.testId}
            aria-current={on ? "page" : undefined}
            className={cn("font-slant relative flex min-h-[54px] shrink-0 items-center gap-2 px-2.5 text-[17px] whitespace-nowrap no-underline md:px-[18px] md:text-xl", on ? "text-ink" : "text-ink-2 hover:text-ink")}
          >
            {it.label}
            {on && <ActiveMark className="right-2.5 -bottom-0.5 left-2.5" />}
          </Link>
        );
      })}
      {extra && <span className="ml-auto flex shrink-0 items-center pr-3 md:pr-0">{extra}</span>}
    </nav>
  );
}

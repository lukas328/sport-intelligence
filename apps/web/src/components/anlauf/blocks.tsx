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

/** Inline text link: ink, underlined. */
export const linkClass = "font-bold text-ink underline decoration-[1.5px] underline-offset-4";

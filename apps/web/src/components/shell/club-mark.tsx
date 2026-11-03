import { contrastText } from "@/lib/color";
import { cn } from "@/lib/utils";

/** Club logo, or a monogram on the club colour. */
export function ClubMark({ org, className }: { org: { id: string; name: string; has_logo: boolean; primary_color: string }; className?: string }) {
  const initials = org.name
    .replace(/^(HC|TV|TSV|SG|HSG|HV|SC|BSV|TSG|KTV|STV|LC)\s+/i, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
  if (org.has_logo) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={`/v1/orgs/${org.id}/logo`} alt="" className={cn("size-9 shrink-0 rounded-xl bg-raised object-contain ring-1 ring-border", className)} />
    );
  }
  return (
    <span
      aria-hidden
      className={cn("grid size-9 shrink-0 place-items-center rounded-xl text-[0.8125rem] font-bold font-wide", className)}
      style={{ background: org.primary_color, color: contrastText(org.primary_color) }}
    >
      {initials || "•"}
    </span>
  );
}

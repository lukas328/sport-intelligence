import { cn } from "@/lib/utils";

export function initialsOf(name: string): string {
  return name
    .replace(/^(HC|TV|TSV|SG|HSG|HV|SC|BSV|TSG|KTV|STV|LC)\s+/i, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
}

/** Short name on the crest: "HC Zürichsee" becomes HCZ, "Handball Wädenswil" HW. */
export function crestText(name: string): string {
  const m = /^(HC|TV|TSV|SG|HSG|HV|SC|BSV|TSG|KTV|STV|LC)\s+(.*)$/i.exec(name.trim());
  if (m) return (m[1]!.toUpperCase() + initialsOf(m[2]!).slice(0, 1)).slice(0, 4);
  return initialsOf(name).slice(0, 3);
}

/**
 * The crest: the club logo, or the club's short name on a shield in the club colour
 * (Anlauf, the frame). Colours from the club scope (lib/color.ts kitVars).
 */
export function ClubMark({ org, className }: { org: { id: string; name: string; has_logo: boolean; primary_color: string }; className?: string }) {
  if (org.has_logo) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={`/v1/orgs/${org.id}/logo`} alt="" className={cn("h-[38px] w-[34px] shrink-0 object-contain", className)} />
    );
  }
  return (
    <span
      aria-hidden
      data-crest=""
      className={cn(
        "grid h-[38px] w-[34px] shrink-0 place-items-center bg-club font-display text-xs font-extrabold text-club-ink italic shadow-[inset_0_0_0_2px_var(--club-edge)] [clip-path:polygon(0_0,100%_0,100%_74%,50%_100%,0_74%)]",
        className,
      )}
    >
      {crestText(org.name) || "HC"}
    </span>
  );
}

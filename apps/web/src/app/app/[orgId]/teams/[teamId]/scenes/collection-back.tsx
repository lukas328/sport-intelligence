import { ArrowLeft } from "lucide-react";
import Link from "next/link";

/** The way back to the collection the scenes were opened for («Szene dazu», A5). */
export function CollectionBack({ href, label }: { href: string; label: string }) {
  return (
    <p className="m-0 mb-6">
      <Link href={href} className="inline-flex min-h-11 items-center gap-2 font-bold text-ink underline decoration-[1.5px] underline-offset-4" data-testid="back-to-collection">
        <ArrowLeft aria-hidden className="size-[18px] shrink-0" strokeWidth={2.4} />
        {label}
      </Link>
    </p>
  );
}

"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { colourChoicePath, dismissColourHint, shouldOfferColour, storedColourHint } from "@/lib/colour-hint";

/**
 * «Vereinsfarbe wählen» (decision E8): one quiet line under the frame for the admin of a club that
 * never chose its colour; it leads to the choice on the club page and can be closed. Nothing shows
 * before the browser has said what it remembers (no flash on every page).
 */
export function ColourHint({ orgId, colorChosen, isAdmin }: { orgId: string; colorChosen: boolean; isAdmin: boolean }) {
  const t = useTranslations("shell");
  const path = usePathname();
  const [stored, setStored] = useState<{ later: boolean; off: boolean } | null>(null);
  useEffect(() => setStored(storedColourHint(orgId)), [orgId]);
  if (!stored) return null;
  const show = shouldOfferColour({ colorChosen, isAdmin, ...stored, onChoicePage: path === `/app/${orgId}/club` });
  if (!show) return null;
  return (
    <div className="border-b border-rule bg-surface" data-testid="colour-hint">
      <p className="mx-auto m-0 flex max-w-[1440px] flex-wrap items-center gap-x-4 gap-y-1 px-4 py-1 text-[15px] md:px-8">
        <span className="mr-auto min-w-0">{t("colourHint")}</span>
        <Link href={colourChoicePath(orgId)} className="inline-flex min-h-11 items-center font-bold underline decoration-[1.5px] underline-offset-4">
          {t("colourHintAction")}
        </Link>
        <button
          type="button"
          className="inline-grid size-11 cursor-pointer place-items-center text-ink-2 hover:text-ink"
          aria-label={t("colourHintClose")}
          onClick={() => {
            dismissColourHint(orgId);
            setStored({ ...stored, off: true });
          }}
        >
          <X aria-hidden className="size-5" strokeWidth={2.2} />
        </button>
      </p>
    </div>
  );
}

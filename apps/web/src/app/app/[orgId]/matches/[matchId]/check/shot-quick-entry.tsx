"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/button";
import { quickQueue } from "@/lib/shot-candidates";
import { useShotCandidates } from "../shot-candidates";

/** «7 Würfe schnell prüfen»: the way into the quick shot review, once the analysis has open
 * shots to ask about; nothing otherwise. */
export function ShotQuickEntry({ orgId, matchId, primary = false }: { orgId: string; matchId: string; primary?: boolean }) {
  const t = useTranslations("shotQuick");
  const q = useShotCandidates(orgId, matchId);
  const n = q.data ? quickQueue(q.data).length : 0;
  if (n === 0) return null;
  return (
    <div className="space-y-2" data-testid="shot-quick-entry">
      <Link href={`/app/${orgId}/matches/${matchId}/check?shots=1`} className={buttonClass(primary ? "primary" : "secondary")} data-testid="shot-quick-link">
        {t("entry", { n })}
      </Link>
      <p className="m-0 text-[15px] text-ink-2">{t("entryHint")}</p>
    </div>
  );
}

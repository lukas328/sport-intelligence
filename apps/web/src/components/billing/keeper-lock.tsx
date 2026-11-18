"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Lock } from "lucide-react";
import { useOptionalShell } from "@/components/shell/context";
import { EmptyState } from "@/components/ui/card";
import { hasFeature } from "@/lib/plan-features";

/**
 * Whether the club's plan has the goalkeeper module (plan feature `goalkeepers`: Team and Verein,
 * not Gratis; Lukas, 18.11.2026). Outside the app frame (shared views) the link decides.
 */
export function useKeeperModule(): boolean {
  return hasFeature(useOptionalShell()?.org.features, "goalkeepers");
}

/** Shown instead of a goalkeeper block the plan does not include, with the way to the plan. */
export function KeeperLock({ orgId, className }: { orgId: string; className?: string }) {
  const t = useTranslations("billing");
  return (
    <div data-testid="keeper-lock" className={className}>
      <EmptyState icon={<Lock aria-hidden />} title={t("keepersLocked")}>
        {t("keepersLockedText")}{" "}
        <Link href={`/app/${orgId}/club/billing`} className="font-semibold text-ink underline underline-offset-4" data-testid="keeper-lock-plan">
          {t("keepersLockedLink")}
        </Link>
      </EmptyState>
    </div>
  );
}

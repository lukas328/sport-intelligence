import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";

/** Shown instead of a feature the current plan does not include. */
export async function PlanHint({ orgId }: { orgId: string }) {
  const t = await getTranslations();
  return (
    <EmptyState title={t("errors.plan-required")}>
      <Link href={`/app/${orgId}/settings#billing`} className="underline underline-offset-4">
        {t("billing.title")}
      </Link>
    </EmptyState>
  );
}

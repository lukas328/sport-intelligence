import { useTranslations } from "next-intl";

/** Opponent name for display; trainings (addendum 01, 4.8) have no opponent. */
export function useOpponentName(): (m: { opponent: { name: string } | null }) => string {
  const t = useTranslations("matches");
  return (m) => m.opponent?.name ?? t("training");
}

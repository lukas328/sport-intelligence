import Link from "next/link";
import { useTranslations } from "next-intl";
import { linkClass } from "@/components/anlauf/blocks";

/**
 * «Das ist ein Beispiel» on the example match of «Demo-Spiel ansehen» (app review R1): its data
 * is made up, it counts nowhere, and the way back to the team's own matches is one tap away.
 */
export function ExampleBanner({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("anlauf");
  return (
    <section role="note" aria-label={t("exampleTitle")} className="max-w-[66ch] space-y-1.5 border-l-4 border-attn pl-4" data-testid="example-banner">
      <p className="m-0 text-[19px] font-bold">{t("exampleTitle")}</p>
      <p className="m-0 text-[17px]">{t("exampleBody")}</p>
      <Link href={`/app/${orgId}/teams/${teamId}/matches`} className={`${linkClass} inline-flex min-h-11 items-center`} data-testid="example-back">
        {t("exampleBack")}
      </Link>
    </section>
  );
}

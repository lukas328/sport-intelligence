"use client";

import { Image as ImageIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { Button } from "@/components/ui/button";

/**
 * A match without video still gives the team something today (review R39): the Spielkarte as a
 * picture for the team chat and the Kurzbericht to copy, both from the report. Shown above the
 * way to the video, so the coach sees first what already works.
 */
export function TodayBlock({ onPicture, report }: { onPicture?: () => void; report: ReactNode }) {
  const t = useTranslations("anlauf");
  if (!onPicture && !report) return null;
  return (
    <section className="space-y-4" data-testid="today-block">
      <SectionHead title={t("todayTitle")} note={t("todayNote")} />
      <p className="m-0 max-w-[62ch] text-[17px]">{t("todayText")}</p>
      {onPicture && (
        <Button variant="secondary" onClick={onPicture} data-testid="today-card">
          <ImageIcon aria-hidden />
          {t("todayCard")}
        </Button>
      )}
      {report}
    </section>
  );
}

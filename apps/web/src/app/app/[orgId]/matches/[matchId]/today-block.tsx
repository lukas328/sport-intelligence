"use client";

import { Image as ImageIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { Button } from "@/components/ui/button";
import { PictureStatus, usePictureAction, type PictureResult } from "./picture-action";

/**
 * A match without video still gives the team something today (review R39): the Spielkarte as a
 * picture for the team chat and the Kurzbericht to copy, both from the report. Shown above the
 * way to the video, so the coach sees first what already works.
 */
export function TodayBlock({ onPicture, report }: { onPicture?: () => Promise<PictureResult>; report: ReactNode }) {
  const t = useTranslations("anlauf");
  const picture = usePictureAction(onPicture);
  if (!onPicture && !report) return null;
  return (
    <section className="space-y-4" data-testid="today-block">
      <SectionHead title={t("todayTitle")} note={t("todayNote")} />
      <p className="m-0 max-w-[62ch] text-[17px]">{t("todayText")}</p>
      {picture.run && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Button variant="secondary" onClick={() => void picture.run?.()} loading={picture.busy} data-testid="today-card">
            {!picture.busy && <ImageIcon aria-hidden />}
            {t("todayCard")}
          </Button>
          <PictureStatus busy={picture.busy} result={picture.result} />
        </div>
      )}
      {report}
    </section>
  );
}

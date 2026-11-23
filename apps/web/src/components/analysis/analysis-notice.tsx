"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { linkClass } from "@/components/anlauf/blocks";
import { buttonClass } from "@/components/ui/button";
import { sitePage, useSiteConfig } from "@/lib/site-config";
import { cn } from "@/lib/utils";

/** Why the analysis asks little or nothing: graphics.notice (second round A6, A7), or the failure
 * code of a file in the progress (A3). */
export type Notice = { reason: string; failed?: boolean; duration_s?: number | null; limit_s?: number | null };

/** The reasons the court is missing: setting its four corners by hand is what helps now. */
const COURT_REASONS = new Set(["camera_motion", "no_floor", "flat_view", "court", "calibration"]);
const KNOWN = new Set([...COURT_REASONS, "few_people", "no_play", "timeout", "stalled", "unreadable", "too_short", "too_long", "generic"]);

export function noticeKey(reason: string): string {
  return KNOWN.has(reason) ? reason : "generic";
}

/** Whether setting the corners by hand helps with this notice. */
export function cornersHelp(n: Notice): boolean {
  return COURT_REASONS.has(n.reason);
}

/** The two sentences of a notice: what happened, in the coach's words, and what helps. */
export function useNoticeWords() {
  const t = useTranslations("analysisNotice");
  return (n: Notice): { title: string; help: string } => {
    const key = noticeKey(n.reason);
    if (key === "timeout") {
      const hours = Math.max(1, Math.round((n.limit_s ?? 6 * 3600) / 3600));
      const minutes = n.duration_s ? Math.round(n.duration_s / 60) : null;
      return { title: minutes != null ? t("title_timeout", { minutes, hours }) : t("title_timeoutNoLength", { hours }), help: t("help_timeout") };
    }
    return { title: t(`title_${key}` as "title_court"), help: t(`help_${key}` as "help_court") };
  };
}

/**
 * The honest word instead of questions (A6, A7): what the analysis could not do, why, and what
 * helps: how to film next time (the website's page «Aufnahme») and, where the court is missing,
 * setting its corners by hand (`cornersHref`, the court question in Prüfen).
 */
export function AnalysisNotice({
  notice,
  cornersHref,
  lead,
  className,
  plain = false,
  testId = "analysis-notice",
}: {
  notice: Notice;
  cornersHref?: string | null;
  lead?: string;
  className?: string;
  /** inside a block that already has its edge (the failed file in the progress) */
  plain?: boolean;
  testId?: string;
}) {
  const t = useTranslations("analysisNotice");
  const words = useNoticeWords()(notice);
  const site = useSiteConfig();
  const locale = useLocale();
  const corners = cornersHref && cornersHelp(notice);
  return (
    <section className={cn("max-w-[62ch] space-y-3", !plain && "border-l-4 border-attn pl-4", className)} data-testid={testId} data-reason={notice.reason}>
      {lead && <p className="m-0 text-[15px] font-semibold text-ink-2">{lead}</p>}
      <p className="m-0 text-[19px] font-bold">{words.title}</p>
      <p className="m-0 text-[17px]">{words.help}</p>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        {corners && (
          <Link href={cornersHref} className={buttonClass("primary")} data-testid="notice-corners">
            {t("corners")}
          </Link>
        )}
        <a href={sitePage(site?.site_url, locale, "aufnahme/")} target="_blank" rel="noreferrer" className={cn(linkClass, "inline-flex min-h-11 items-center")} data-testid="notice-film">
          {t("filmLink")}
        </a>
      </div>
    </section>
  );
}

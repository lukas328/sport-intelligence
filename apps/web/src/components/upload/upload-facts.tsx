"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useOptionalShell } from "@/components/shell/context";
import { formatBytes } from "@/lib/format";
import { useSiteConfig } from "@/lib/site-config";
import { cn } from "@/lib/utils";

/**
 * What a coach asks before the upload (review R33): which files, how large, what happens when the
 * phone goes to sleep, what the analysis costs. No duration of the analysis: it is not measured
 * yet, and a number nobody measured would be a promise.
 */
export function UploadFacts({ className }: { className?: string }) {
  const t = useTranslations("uploadFacts");
  const site = useSiteConfig();
  const shell = useOptionalShell();
  const admin = shell?.org.my_role === "org_admin";
  const rows = [
    { key: "formats", text: t("formats") },
    { key: "size", text: site?.max_video_bytes ? t("size", { max: formatBytes(site.max_video_bytes) }) : t("sizeUnknown") },
    { key: "phone", text: t("phone") },
    { key: "analysis", text: t("analysis") },
  ];
  return (
    <div className={cn("max-w-[62ch] border-l-4 border-rule pl-3", className)} data-testid="upload-facts">
      <p className="m-0 text-[15px] font-bold">{t("title")}</p>
      <dl className="m-0 mt-1 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-[15px]">
        {rows.map((r) => (
          <div key={r.key} className="contents">
            <dt className="font-semibold">{t(`label_${r.key}` as "label_formats")}</dt>
            <dd className="m-0 text-ink-2">
              {r.text}
              {r.key === "analysis" && admin && shell && (
                <>
                  {" "}
                  <Link href={`/app/${shell.org.id}/club/billing`} className="font-semibold text-ink underline underline-offset-4">
                    {t("billing")}
                  </Link>
                </>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

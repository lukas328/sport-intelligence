"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { buttonClass } from "@/components/ui/button";
import type { NextTask } from "@/lib/next-task";

/**
 * The one next task under the head of a match page (L5): what is open, in a few words, and the
 * button that does it. Nothing when nothing is open.
 */
export function NextTaskLine({ task, base, onUpload }: { task: NextTask; base: string; onUpload: () => void }) {
  const t = useTranslations("nextTask");
  if (!task) return null;
  const action =
    task.kind === "checks" ? (
      <Link href={`${base}/check`} className={buttonClass("primary")} data-testid="next-task-action">
        {t("checksAction")}
      </Link>
    ) : task.kind === "spots" ? (
      <Link href={`${base}/check?spots=1`} className={buttonClass("primary")} data-testid="next-task-action">
        {t("spotsAction")}
      </Link>
    ) : task.kind === "prepare" ? (
      <Link href={`${base}/scouting`} className={buttonClass("primary")} data-testid="next-task-action">
        {t("prepareAction")}
      </Link>
    ) : (
      <button type="button" onClick={onUpload} className={buttonClass("primary")} data-testid="next-task-action">
        {t("uploadAction")}
      </button>
    );
  const text = task.kind === "checks" ? t("checks", { n: task.n }) : task.kind === "spots" ? t("spots", { n: task.n }) : t(task.kind);
  return (
    <section className="flex flex-wrap items-center gap-x-5 gap-y-3 border-l-4 border-attn bg-paper px-4 py-3" aria-label={t("label")} data-testid="next-task" data-kind={task.kind}>
      <p className="m-0 text-[17px] font-bold">{text}</p>
      {action}
    </section>
  );
}

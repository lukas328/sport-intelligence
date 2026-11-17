"use client";

import { templateDoc, type PlayDoc, type Template } from "@handball/tactics";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Board } from "@/components/tactics/board";
import { TokenDot } from "@/components/tactics/tool-icon";
import { commonFrom, previewFrom } from "@/lib/play-preview";

/** The first frame of a play, small and without controls, cut to where the players are (R12). */
export function PlayPreview({ doc, label, from }: { doc: PlayDoc; label: string; from?: number }) {
  const f = doc.frames[0];
  if (!f) return null;
  // full-court plays stay across in the small card (upright they would be twice as tall as the others)
  return (
    <div aria-hidden className="pointer-events-none">
      <Board
        frame={f}
        court={doc.court}
        label={label}
        orientation={doc.court === "full" ? "landscape" : "portrait"}
        from={from ?? previewFrom(doc)}
      />
    </div>
  );
}

/**
 * «Wir» is always one colour, whether we attack or defend: the line above the templates says so,
 * with the two colours (review R15).
 */
export function TemplateLegend() {
  const t = useTranslations("tactics");
  return (
    <p
      className="m-0 flex flex-wrap items-center gap-x-4 gap-y-1 text-[15px] text-ink-2"
      data-testid="template-legend"
    >
      <span className="inline-flex items-center gap-1.5">
        <TokenDot side="own" />
        {t("own")}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <TokenDot side="opp" />
        {t("opp")}
      </span>
      <span>{t("legendRoles")}</span>
    </p>
  );
}

/** The templates as small pictures; each opens a new play from it. */
export function TemplateGrid({
  orgId,
  teamId,
  templates,
  columns = "sm:grid-cols-2 lg:grid-cols-4",
}: {
  orgId: string;
  teamId: string;
  templates: readonly Template[];
  columns?: string;
}) {
  const t = useTranslations("tactics");
  const locale = useLocale();
  const docs = templates.map((tpl) => templateDoc(tpl, locale));
  const from = commonFrom(docs);
  return (
    <ul className={`m-0 grid list-none gap-x-6 gap-y-6 p-0 ${columns}`}>
      {templates.map((tpl, i) => (
        <li key={tpl.id}>
          <Link
            href={`/app/${orgId}/teams/${teamId}/plays/new?template=${tpl.id}`}
            className="block space-y-2 border-t border-foreground/30 pt-2 hover:text-accent"
            aria-label={`${t("fromTemplate")}: ${t(`tpl_${tpl.id}`)}`}
          >
            <PlayPreview doc={docs[i]!} label={t(`tpl_${tpl.id}`)} from={docs[i]!.court === "half" ? from : undefined} />
            <p className="text-sm font-medium">{t(`tpl_${tpl.id}`)}</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}

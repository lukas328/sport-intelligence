"use client";

import type { Drill, Lang } from "@handball/tactics";
import { useTranslations } from "next-intl";
import { Board } from "@/components/tactics/board";
import { cn } from "@/lib/utils";

export const asLang = (locale: string): Lang => (["de-CH", "fr", "en"].includes(locale) ? (locale as Lang) : "de-CH");

/** The drill's court sketch on the tactics board (read-only, same look as the plays). */
export function DrillSketchView({ drill, lang, className }: { drill: Drill; lang: Lang; className?: string }) {
  const t = useTranslations("drills");
  const s = drill.sketch;
  // show the part of the half that is used: from 2 m behind the furthest mark, never less than 13 m
  const xs = [...s.tokens.map((k) => k.x), ...s.arrows.flatMap((a) => a.points.map((p) => p[0])), ...s.cones.map((c) => c[0]), ...(s.ball ? [s.ball.x] : [])];
  const from = Math.floor(Math.min(27, ...xs.map((x) => x - 2)));
  return (
    <div className={cn("pointer-events-none", className)}>
      <Board
        frame={{ tokens: s.tokens, ball: s.ball, arrows: s.arrows, note: "", duration_ms: 2000 }}
        court={s.court}
        cones={s.cones}
        from={s.court === "half" ? from : undefined}
        orientation={s.court === "full" ? "landscape" : "portrait"}
        label={t("sketchLabel", { name: drill.name[lang] })}
      />
    </div>
  );
}

/** Focus, minutes, players and level in one line. */
export function DrillMeta({ drill, className }: { drill: Drill; className?: string }) {
  const t = useTranslations("drills");
  return (
    <p className={cn("text-[15px] text-muted", className)}>
      {drill.focus.map((f) => t(`focus_${f}`)).join(" · ")} · {t("minutes", { minutes: drill.minutes })} · {t("players", { players: drill.players })} · {t(`level_${drill.level}`)}
    </p>
  );
}

/** Set-up, procedure, coaching points and variants. */
export function DrillText({ drill, lang }: { drill: Drill; lang: Lang }) {
  const t = useTranslations("drills");
  const rows = [
    ["setup", drill.setup],
    ["procedure", drill.procedure],
    ["coaching", drill.coaching],
    ["variants", drill.variants],
  ] as const;
  return (
    <dl className="space-y-2 text-[15px]">
      {rows.map(([k, text]) => (
        <div key={k}>
          <dt className="font-semibold">{t(k)}</dt>
          <dd className="m-0">{text[lang]}</dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * A drill of the library: sketch, name and facts; the description opens below («So geht's»).
 * `id` makes it a link target (/drills#<id>), which opens it.
 */
export function DrillCard({ drill, lang, open, compact = false }: { drill: Drill; lang: Lang; open?: boolean; compact?: boolean }) {
  const t = useTranslations("drills");
  return (
    <article id={drill.id} className="grid scroll-mt-20 grid-cols-[6.5rem_minmax(0,1fr)] gap-x-4 gap-y-2 sm:grid-cols-[9rem_minmax(0,1fr)]" data-testid="drill">
      <DrillSketchView drill={drill} lang={lang} className="row-span-2 self-start" />
      <div className="min-w-0 space-y-1">
        <h3 className="text-lg leading-tight">{drill.name[lang]}</h3>
        <DrillMeta drill={drill} />
        {!compact && <p className="text-[15px]">{drill.setup[lang]}</p>}
      </div>
      <details className="col-span-2 group sm:col-span-1 sm:col-start-2" open={open}>
        <summary className="inline-flex min-h-11 cursor-pointer items-center text-[15px] font-semibold underline underline-offset-4">{t("howTo")}</summary>
        <div className="mt-2">
          <DrillText drill={drill} lang={lang} />
        </div>
      </details>
    </article>
  );
}

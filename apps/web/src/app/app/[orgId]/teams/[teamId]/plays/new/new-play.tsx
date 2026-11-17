"use client";

import { TEMPLATES, templateDoc, validate, type PlayDoc } from "@handball/tactics";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { EMPTY_DOC, PlayEditor } from "@/components/tactics/play-editor";
import { TemplateGrid, TemplateLegend } from "@/components/tactics/play-preview";
import { FROM_VIDEO_KEY } from "@/lib/play-from-video";

/** New play from scratch, from a template (?template=id) or from a video moment (?from=video). */
export function NewPlay({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("tactics");
  const locale = useLocale();
  const params = useSearchParams();
  const tpl = TEMPLATES.find((x) => x.id === params.get("template"));
  const [video, setVideo] = useState<
    { doc: PlayDoc; match_id: string; t_ms: number } | null | undefined
  >(undefined);
  useEffect(() => {
    if (params.get("from") !== "video") return setVideo(null);
    try {
      const raw = window.sessionStorage.getItem(FROM_VIDEO_KEY);
      const parsed = raw
        ? (JSON.parse(raw) as { doc: PlayDoc; match_id: string; t_ms: number })
        : null;
      setVideo(parsed && validate(parsed.doc).length === 0 ? parsed : null);
    } catch {
      setVideo(null);
    }
  }, [params]);
  if (video === undefined) return null;
  const blank = !tpl && !video;
  return (
    <div className="space-y-6">
      {/* the empty board says «starte mit einer Vorlage»: the templates are right here (review R14) */}
      {blank && (
        <details className="border-y border-rule py-2" data-testid="template-picker">
          <summary className="min-h-11 cursor-pointer content-center font-bold underline decoration-[1.5px] underline-offset-4">
            {t("pickTemplate")}
          </summary>
          <div className="space-y-3 pt-3 pb-2">
            <TemplateLegend />
            <TemplateGrid
              orgId={orgId}
              teamId={teamId}
              templates={TEMPLATES}
              columns="grid-cols-2 sm:grid-cols-3 lg:grid-cols-6"
            />
          </div>
        </details>
      )}
      <PlayEditor
        key={tpl?.id ?? "blank"}
        orgId={orgId}
        teamId={teamId}
        editable
        initialDoc={video?.doc ?? (tpl ? templateDoc(tpl, locale) : EMPTY_DOC)}
        initialMeta={
          tpl
            ? {
                name: t(`tpl_${tpl.id}`),
                category: tpl.category,
                formation: tpl.formation,
                tags: tpl.tags,
              }
            : undefined
        }
        source={video ? { match_id: video.match_id, t_ms: video.t_ms } : null}
      />
    </div>
  );
}

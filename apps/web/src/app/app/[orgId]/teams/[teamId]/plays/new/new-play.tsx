"use client";

import { TEMPLATES, validate, type PlayDoc } from "@handball/tactics";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { EMPTY_DOC, PlayEditor } from "@/components/tactics/play-editor";
import { FROM_VIDEO_KEY } from "@/lib/play-from-video";

/** New play from scratch, from a template (?template=id) or from a video moment (?from=video). */
export function NewPlay({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("tactics");
  const params = useSearchParams();
  const tpl = TEMPLATES.find((x) => x.id === params.get("template"));
  const [video, setVideo] = useState<{ doc: PlayDoc; match_id: string; t_ms: number } | null | undefined>(undefined);
  useEffect(() => {
    if (params.get("from") !== "video") return setVideo(null);
    try {
      const raw = window.sessionStorage.getItem(FROM_VIDEO_KEY);
      const parsed = raw ? (JSON.parse(raw) as { doc: PlayDoc; match_id: string; t_ms: number }) : null;
      setVideo(parsed && validate(parsed.doc).length === 0 ? parsed : null);
    } catch {
      setVideo(null);
    }
  }, [params]);
  if (video === undefined) return null;
  return (
    <PlayEditor
      orgId={orgId}
      teamId={teamId}
      editable
      initialDoc={video?.doc ?? tpl?.doc ?? EMPTY_DOC}
      initialMeta={tpl ? { name: t(`tpl_${tpl.id}`), category: tpl.category, formation: tpl.formation, tags: tpl.tags } : undefined}
      source={video ? { match_id: video.match_id, t_ms: video.t_ms } : null}
    />
  );
}

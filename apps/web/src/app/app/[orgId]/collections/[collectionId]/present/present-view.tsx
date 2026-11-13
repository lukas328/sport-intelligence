"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { VideoPlayer } from "@/components/video/player";
import { api } from "@/lib/client";

type Collection = Schemas["CollectionOut"];
type Item = Schemas["ItemOut"];

/**
 * «Am Bildschirm zeigen» (SPEC 6, 7.7, UX test B04): the collection on the big screen, nothing
 * around it. Scenes play one after the other, a note stands as a board, a play as its name.
 * Space or the right arrow key goes on, the left one back, Esc leaves; «Vollbild» uses the whole
 * screen.
 */
export function PresentView({ orgId, collection, onClose }: { orgId: string; collection: Collection; onClose?: () => void }) {
  const t = useTranslations("collections");
  const router = useRouter();
  const items = collection.items;
  const [k, setK] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const item: Item | undefined = items[k];
  const next = useCallback(() => setK((x) => Math.min(x + 1, items.length - 1)), [items.length]);
  const prev = useCallback(() => setK((x) => Math.max(x - 1, 0)), []);
  const back = `/app/${orgId}/collections/${collection.id}`;
  // a scene list played from the search closes in place; a collection goes back to its page
  const leave = useCallback(() => (onClose ? onClose() : router.push(back)), [onClose, router, back]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") (e.preventDefault(), next());
      else if (e.key === "ArrowLeft" || e.key === "PageUp") (e.preventDefault(), prev());
      else if (e.key === "Escape" && !document.fullscreenElement) leave();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev, leave]);
  return (
    <div ref={box} className="flex min-h-[calc(100dvh-60px)] flex-col bg-court-bar text-court-text" data-testid="present-view">
      <div className="flex min-h-12 items-center justify-between gap-3 px-4 py-2 text-[15px] md:px-8">
        <b className="font-slant truncate text-xl text-white">{collection.title}</b>
        <span className="flex items-center gap-3">
          <span className="font-mono">{t("presentOf", { n: k + 1, total: items.length })}</span>
          <button type="button" onClick={() => void box.current?.requestFullscreen?.()} className="min-h-11 cursor-pointer border-[1.5px] border-[#4a5058] px-3 font-bold text-white">
            {t("fullscreen")}
          </button>
          <button type="button" onClick={leave} className="min-h-11 cursor-pointer border-[1.5px] border-[#4a5058] px-3 font-bold text-white" data-testid="present-close">
            {t("close")}
          </button>
        </span>
      </div>
      <div className="grid flex-1 place-items-center px-4 md:px-8">
        {!item ? (
          <p className="text-2xl">{t("empty")}</p>
        ) : item.scene ? (
          <SceneOnScreen key={`${k}-${item.scene.clip_id}`} orgId={orgId} scene={item.scene} text={item.text ?? null} onEnd={next} />
        ) : (
          <div className="max-w-[60ch] text-center">
            {item.play && <p className="font-slant mb-4 text-[34px] text-white md:text-[58px]">{item.play.name}</p>}
            {item.text && <p className="font-slant text-[28px] leading-tight text-white whitespace-pre-line md:text-[44px]">{item.text}</p>}
          </div>
        )}
      </div>
      <div className="flex justify-center gap-3 px-4 py-4">
        <button type="button" onClick={prev} disabled={k === 0} className="min-h-12 cursor-pointer border-2 border-[#4a5058] px-5 font-bold text-white disabled:opacity-40">
          {t("prev")}
        </button>
        <button type="button" onClick={next} disabled={k >= items.length - 1} className="min-h-12 cursor-pointer border-2 border-white bg-white px-5 font-bold text-court-bar disabled:opacity-40" data-testid="present-next">
          {t("next")}
        </button>
      </div>
    </div>
  );
}

function SceneOnScreen({ orgId, scene, text, onEnd }: { orgId: string; scene: Schemas["SceneOut"]; text: string | null; onEnd: () => void }) {
  // the scene's video: the main camera of its match
  const match = useQuery({
    queryKey: ["match", scene.match_id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: scene.match_id } } })).data ?? null,
  });
  const video = match.data?.videos.find((v) => v.role === "main" && v.status === "ready");
  return (
    <div className="w-full max-w-[1400px]">
      {video ? (
        <VideoPlayer src={`/v1/orgs/${orgId}/videos/${video.id}/media/hls/master.m3u8`} window={{ start_ms: scene.start_ms, end_ms: scene.end_ms }} onWindowEnd={onEnd} autoPlay />
      ) : (
        <div className="aspect-video bg-black" aria-busy={match.isLoading} />
      )}
      {(scene.title || text) && (
        <p className="mt-3 border-l-4 border-white pl-3 text-xl text-white">
          {scene.title && <b className="mr-2">{scene.title}</b>}
          {text}
        </p>
      )}
    </div>
  );
}

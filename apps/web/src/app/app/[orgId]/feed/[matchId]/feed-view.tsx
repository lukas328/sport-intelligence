"use client";

import { BackLink } from "@/components/ui/back-link";
import { track } from "@/lib/analytics";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { SpotlightOverlay } from "@/components/video/spotlight";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

/**
 * "Deine Szenen" (addendum 01, 4.7): mobile first, one scene per screen. The player rates the match
 * first; the coach's comments appear only afterwards. Youth wording is developmental.
 */
export function FeedView({ orgId, matchId, playerId }: { orgId: string; matchId: string; playerId: string | null }) {
  const t = useTranslations("feed");
  const qc = useQueryClient();
  const key = ["feed", orgId, matchId, playerId];
  const [index, setIndex] = useState(0);
  const [rating, setRating] = useState(0);
  const touch = useRef<number | null>(null);
  const q = useQuery({
    queryKey: key,
    queryFn: async () =>
      (
        await api.GET("/v1/orgs/{org_id}/matches/{match_id}/feed/me", {
          params: { path: { org_id: orgId, match_id: matchId }, query: playerId ? { player_id: playerId } : {} },
        })
      ).data ?? null,
  });
  const assess = useMutation({
    mutationFn: async (body: { rating: number; text: string | null }) =>
      (
        await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/self-assessment", {
          params: { path: { org_id: orgId, match_id: matchId } },
          body: { ...body, player_id: playerId },
        })
      ).data,
    onSuccess: (data) => {
      qc.setQueryData(key, data);
      void qc.invalidateQueries({ queryKey: ["my-feeds", orgId] });
    },
  });
  const feed = q.data;
  const player = useRef<PlayerHandle>(null);
  const analysis = useQuery({
    queryKey: ["analysis", feed?.video_id],
    enabled: Boolean(feed?.video_id),
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: orgId, video_id: feed!.video_id! } } })).data ?? null,
  });
  const a = analysis.data;
  // spotlight on the player automatically (4.7), when the analysis identified their track
  const myTrack = a?.tracks.find((tr) => tr.player_id === feed?.player_id);
  if (q.isLoading) return <p className="text-muted">{t("loading")}</p>;
  if (!feed) return <Alert>{t("none")}</Alert>;
  const scene = feed.items[index];
  const reasonKey = (r: string) => (feed.youth ? `youth_${r}` : `reason_${r}`);
  if (typeof window !== "undefined" && !sessionStorage.getItem(`hb.fa.${matchId}`)) {
    sessionStorage.setItem(`hb.fa.${matchId}`, "1");
    track("player_active");
  }

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const text = String(new FormData(e.currentTarget).get("text") ?? "").trim();
    if (rating) assess.mutate({ rating, text: text || null });
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <BackLink fallback={`/app/${orgId}/feed`} />
      <h1 className="text-2xl font-bold sm:text-[1.75rem]">{t("title")}</h1>
      {!feed.self_assessment && (
        <form onSubmit={submit} className="space-y-3 rounded-lg bg-raised border border-border p-4" aria-label={t("assessTitle")}>
          <h2 className="font-semibold">{t("assessTitle")}</h2>
          <p className="text-sm text-muted">{t("assessIntro")}</p>
          <fieldset className="flex gap-2">
            <legend className="sr-only">{t("rating")}</legend>
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                aria-pressed={rating === n}
                aria-label={t("ratingN", { n })}
                onClick={() => setRating(n)}
                className={cn("size-12 rounded-full border text-lg font-semibold", rating === n ? "border-foreground bg-foreground text-background" : "border-border bg-raised hover:bg-surface")}
              >
                {n}
              </button>
            ))}
          </fieldset>
          <label className="block text-sm font-medium" htmlFor="assess-text">
            {t("sentence")}
          </label>
          <textarea id="assess-text" name="text" maxLength={500} rows={2} className="w-full rounded-md bg-raised p-3 ring-1 ring-inset ring-border" />
          <Button type="submit" disabled={!rating} loading={assess.isPending}>
            {t("send")}
          </Button>
          {feed.coach_comments_waiting > 0 && <p className="text-sm text-muted">{t("commentsWaiting", { n: feed.coach_comments_waiting })}</p>}
        </form>
      )}
      {feed.self_assessment && (
        <p className="rounded-md bg-surface px-4 py-2.5 text-sm" data-testid="my-rating">
          {t("yourRating", { n: feed.self_assessment.rating })}
          {feed.self_assessment.text && `: ${feed.self_assessment.text}`}
        </p>
      )}
      {scene && (
        <section
          aria-labelledby="scene-title"
          className="space-y-3"
          data-testid="scene"
          onKeyDown={(e) => {
            if (e.key === "ArrowRight" && index < feed.items.length - 1) setIndex(index + 1);
            if (e.key === "ArrowLeft" && index > 0) setIndex(index - 1);
          }}
          onTouchStart={(e) => (touch.current = e.touches[0]?.clientX ?? null)}
          onTouchEnd={(e) => {
            const start = touch.current;
            const end = e.changedTouches[0]?.clientX;
            touch.current = null;
            if (start == null || end == null || Math.abs(end - start) < 60) return;
            if (end < start && index < feed.items.length - 1) setIndex(index + 1);
            if (end > start && index > 0) setIndex(index - 1);
          }}
        >
          {/* one segment per scene, like a story: where am I, jump anywhere */}
          <ol className="flex gap-1" aria-label={t("sceneN", { n: index + 1, total: feed.items.length })}>
            {feed.items.map((it, i) => (
              <li key={it.id} className="flex-1">
                <button
                  type="button"
                  aria-label={t("sceneN", { n: i + 1, total: feed.items.length })}
                  aria-current={i === index ? "step" : undefined}
                  onClick={() => setIndex(i)}
                  className="block w-full py-2"
                >
                  <span className={cn("block h-1 rounded-full transition-colors", i < index ? "bg-foreground/60" : i === index ? "bg-accent" : "bg-border")} />
                </button>
              </li>
            ))}
          </ol>
          <h2 id="scene-title" className="flex flex-wrap items-center gap-2 text-lg font-bold">
            <span className={cn("rounded-md px-2.5 py-0.5 text-xs font-semibold", scene.positive ? "bg-ok/15 text-ok" : "bg-surface text-muted")}>
              {t("sceneN", { n: index + 1, total: feed.items.length })}
            </span>
            {t(reasonKey(scene.reason) as "reason_goal")}
          </h2>
          {feed.video_id ? (
            <VideoPlayer
              ref={player}
              key={scene.id}
              src={`/v1/orgs/${orgId}/videos/${feed.video_id}/media/hls/master.m3u8`}
              window={{ start_ms: scene.start_ms, end_ms: scene.end_ms }}
              autoPlay
              overlay={
                myTrack && a?.calibration && a.camera !== "moving" && a.chunk_ms ? (
                  <SpotlightOverlay
                    baseUrl={`/v1/orgs/${orgId}/videos/${feed.video_id}/tracks`}
                    chunkMs={a.chunk_ms}
                    homography={a.calibration.homography}
                    imageSize={a.calibration.image_size as [number, number]}
                    track={myTrack.track_no}
                    label=""
                    getTime={() => player.current?.time() ?? 0}
                    showTrail
                  />
                ) : undefined
              }
            />
          ) : (
            <p className="text-muted">{t("noVideo")}</p>
          )}
          {scene.coach_comment && (
            <p className="rounded-md bg-surface px-3 py-2 text-sm" data-testid="coach-comment">
              {t("coach")}: {scene.coach_comment}
            </p>
          )}
          <div className="grid grid-cols-2 gap-3">
            <Button variant="secondary" size="lg" disabled={index === 0} onClick={() => setIndex((i) => i - 1)}>
              <ChevronLeft aria-hidden />
              {t("prev")}
            </Button>
            <Button size="lg" disabled={index >= feed.items.length - 1} onClick={() => setIndex((i) => i + 1)}>
              {t("next")}
              <ChevronRight aria-hidden />
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}

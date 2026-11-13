"use client";

import { BackLink } from "@/components/ui/back-link";
import { ShareButton } from "@/components/sharing/share-button";
import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, EmptyState } from "@/components/ui/card";
import { VideoPlayer } from "@/components/video/player";
import { api } from "@/lib/client";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";

type Playlist = Schemas["PlaylistDetail"];

export function PlaylistView({ orgId, initial, staff }: { orgId: string; initial: Playlist; staff: boolean }) {
  const t = useTranslations("playlists");
  const router = useRouter();
  const qc = useQueryClient();
  const key = ["playlist", initial.id];
  const path = { org_id: orgId, playlist_id: initial.id };
  const { data: pl = initial } = useQuery({
    queryKey: key,
    initialData: initial,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/playlists/{playlist_id}", { params: { path } })).data ?? initial,
  });
  const [index, setIndex] = useState(0);
  const [autoplay, setAutoplay] = useState(false);
  const item = pl.items[index];
  const win = useMemo(() => (item ? { start_ms: item.clip.start_ms, end_ms: item.clip.end_ms } : undefined), [item]);
  const next = useCallback(() => {
    if (index < pl.items.length - 1) {
      setAutoplay(true);
      setIndex((i) => i + 1);
    }
  }, [index, pl.items.length]);

  const refresh = () => void qc.invalidateQueries({ queryKey: key });
  async function move(i: number, dir: -1 | 1) {
    const ids = pl.items.map((x) => x.id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j]!, ids[i]!];
    await api.PUT("/v1/orgs/{org_id}/playlists/{playlist_id}/order", { params: { path }, body: { item_ids: ids } });
    refresh();
  }

  return (
    <div className="space-y-6">
      <BackLink fallback={`/app/${orgId}`} />
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold sm:text-[1.75rem]">{pl.title}</h1>
          <p className="text-sm text-muted">
            {t("items", { count: pl.items.length })} · {pl.shared_with_players ? t("shared") : t("notShared")}
          </p>
        </div>
        {staff && <ShareButton orgId={orgId} teamId={pl.team_id} kind="playlist" targetId={pl.id} />}
        {staff && (
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={async () => {
                await api.PATCH("/v1/orgs/{org_id}/playlists/{playlist_id}", {
                  params: { path },
                  body: { shared_with_players: !pl.shared_with_players },
                });
                refresh();
              }}
            >
              {pl.shared_with_players ? t("unshare") : t("share")}
            </Button>
            <Button
              variant="danger"
              onClick={async () => {
                await api.DELETE("/v1/orgs/{org_id}/playlists/{playlist_id}", { params: { path } });
                router.push(`/app/${orgId}/teams/${pl.team_id}/playlists`);
                router.refresh();
              }}
            >
              {t("delete")}
            </Button>
          </div>
        )}
      </header>
      {pl.items.length === 0 ? (
        <EmptyState title={t("noItems")} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="space-y-2">
            {item?.video_id ? (
              <VideoPlayer
                key={item.video_id}
                src={`/v1/orgs/${orgId}/videos/${item.video_id}/media/hls/master.m3u8`}
                window={win}
                onWindowEnd={next}
                autoPlay={autoplay}
              />
            ) : (
              <p className="text-muted">{t("empty")}</p>
            )}
            <p className="text-sm text-muted" aria-live="polite">
              {t("nowPlaying", { n: index + 1, total: pl.items.length })}
            </p>
          </div>
          <Card className="p-3">
            <ol className="space-y-1 text-sm" data-testid="playlist-items">
              {pl.items.map((it, i) => (
                <li key={it.id} className={cn("p-2", i === index ? "bg-surface" : "")}>
                  <button className="w-full text-left" onClick={() => (setAutoplay(true), setIndex(i))} aria-current={i === index}>
                    <span className="font-medium">{it.clip.title ?? `${t("play")} ${i + 1}`}</span>
                    <span className="block text-xs text-muted">
                      {it.match_label} · {formatClock(it.clip.start_ms)}-{formatClock(it.clip.end_ms)}
                    </span>
                    {it.note && <span className="block text-xs">{it.note}</span>}
                  </button>
                  {staff && (
                    <div className="mt-1 flex gap-2 text-xs">
                      <button className="underline" onClick={() => move(i, -1)} disabled={i === 0}>
                        {t("up")}
                      </button>
                      <button className="underline" onClick={() => move(i, 1)} disabled={i === pl.items.length - 1}>
                        {t("down")}
                      </button>
                      <button
                        className="text-error underline"
                        onClick={async () => {
                          await api.DELETE("/v1/orgs/{org_id}/playlists/{playlist_id}/items/{item_id}", {
                            params: { path: { ...path, item_id: it.id } },
                          });
                          setIndex(0);
                          refresh();
                        }}
                      >
                        {t("remove")}
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </Card>
        </div>
      )}
    </div>
  );
}

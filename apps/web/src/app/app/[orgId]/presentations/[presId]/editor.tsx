"use client";

import { BackLink } from "@/components/ui/back-link";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card, EmptyState } from "@/components/ui/card";
import { Checkbox, Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { isPacked, packPresentation, unpack } from "@/lib/offline-pack";
import { cn } from "@/lib/utils";
import { FileField } from "@/components/ui/file-field";

type Slide = Schemas["SlideOut"];

function slideTitle(s: Slide, t: (k: string, v?: Record<string, string | number>) => string): string {
  const c = s.content as Record<string, unknown>;
  if (s.type === "clip") return t("clipLabel", { from: Math.round(Number(c.in_ms) / 1000), to: Math.round(Number(c.out_ms) / 1000) });
  return String(c.title ?? (c.observation ? t("observation") : t(`type_${s.type}`)));
}

export function PresentationEditor({ orgId, presId }: { orgId: string; presId: string }) {
  const t = useTranslations("presentations");
  const tr = useTranslations();
  const tf = useTranslations("file");
  const locale = useLocale();
  const qc = useQueryClient();
  const key = ["presentation", presId];
  const path = { org_id: orgId, pres_id: presId };
  const [error, setError] = useState<ErrorKey | null>(null);
  const [drag, setDrag] = useState<string | null>(null);
  const [packed, setPacked] = useState(false);
  const [packing, setPacking] = useState<string | null>(null);
  useEffect(() => void isPacked(presId).then(setPacked), [presId]);
  const q = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/presentations/{pres_id}", { params: { path } })).data ?? null,
    refetchInterval: (query) => (query.state.data?.export_status === "queued" ? 3000 : false),
  });
  const p = q.data;
  const plays = useQuery({
    queryKey: ["plays", p?.team_id],
    enabled: Boolean(p?.can_edit),
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/plays", { params: { path: { org_id: orgId, team_id: p!.team_id } } })).data ?? [],
  });
  const refresh = () => void qc.invalidateQueries({ queryKey: key });
  const fail = (e: unknown) => setError(errorKey(e));
  const run = <T,>(fn: () => Promise<{ error?: unknown; data?: T }>) =>
    fn().then((r) => {
      if (r.error) throw r.error;
      setError(null);
      refresh();
      return r.data;
    });

  const order = useMutation({
    mutationFn: (ids: string[]) => run(() => api.PUT("/v1/orgs/{org_id}/presentations/{pres_id}/order", { params: { path }, body: { slide_ids: ids } })),
    onError: fail,
  });
  const add = useMutation({
    mutationFn: (body: Schemas["SlideIn"]) => run(() => api.POST("/v1/orgs/{org_id}/presentations/{pres_id}/slides", { params: { path }, body })),
    onError: fail,
  });
  const patch = useMutation({
    mutationFn: ({ id, content }: { id: string; content: Record<string, unknown> }) =>
      run(() => api.PATCH("/v1/orgs/{org_id}/slides/{slide_id}", { params: { path: { org_id: orgId, slide_id: id } }, body: { content } })),
    onError: fail,
  });
  const remove = useMutation({
    mutationFn: (id: string) => run(() => api.DELETE("/v1/orgs/{org_id}/slides/{slide_id}", { params: { path: { org_id: orgId, slide_id: id } } })),
    onError: fail,
  });
  const share = useMutation({
    mutationFn: (v: boolean) => run(() => api.PATCH("/v1/orgs/{org_id}/presentations/{pres_id}", { params: { path }, body: { shared_with_players: v } })),
    onError: fail,
  });
  const exportMp4 = useMutation({
    mutationFn: () => run(() => api.POST("/v1/orgs/{org_id}/presentations/{pres_id}/export", { params: { path } })),
    onError: fail,
  });

  if (!p) return q.isLoading ? <p className="text-muted">…</p> : <Alert>{tr("errors.not-found")}</Alert>;
  const slides = p.slide_list;

  function move(id: string, to: number) {
    const ids = slides.map((s) => s.id).filter((x) => x !== id);
    ids.splice(Math.max(0, Math.min(to, ids.length)), 0, id);
    order.mutate(ids);
  }

  function addText(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    add.mutate({ type: "text", content: { title: String(f.get("title") ?? ""), body: String(f.get("body") ?? "") } });
    e.currentTarget.reset();
  }

  async function pack() {
    const clips = slides
      .filter((s) => s.type === "clip")
      .map((s) => s.content as { video_id: string; in_ms: number; out_ms: number });
    const extra = slides.flatMap((s) => [
      ...(s.type === "image" ? [`/v1/orgs/${orgId}/slides/${s.id}/image`] : []),
      ...(s.play_id ? [`/v1/orgs/${orgId}/plays/${s.play_id}`] : []),
    ]);
    setPacking("0 %");
    try {
      await packPresentation(orgId, presId, clips, extra, (d, n) => setPacking(`${Math.round((d / n) * 100)} %`));
      setPacked(true);
    } finally {
      setPacking(null);
    }
  }

  return (
    <div className="space-y-5">
      <BackLink fallback={`/app/${orgId}`} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold sm:text-[1.75rem]">{p.title}</h1>
          <p className="text-sm text-muted">{t("slides", { n: slides.length })}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/app/${orgId}/presentations/${presId}/present`} className="bg-accent px-4 py-2 font-medium text-accent-contrast" data-testid="present">
            {t("present")}
          </Link>
          <a href={`/v1/orgs/${orgId}/presentations/${presId}/pdf?lang=${locale}`} className="inline-flex min-h-9 items-center gap-1.5 bg-raised px-4 text-[0.9375rem] font-medium ring-1 ring-inset ring-border hover:bg-surface">
            {t("pdf")}
          </a>
          {p.can_edit &&
            (p.export_status === "ready" ? (
              <a href={`/v1/orgs/${orgId}/presentations/${presId}/export.mp4`} className="inline-flex min-h-9 items-center gap-1.5 bg-raised px-4 text-[0.9375rem] font-medium ring-1 ring-inset ring-border hover:bg-surface">
                {t("mp4Download")}
              </a>
            ) : (
              <Button variant="secondary" loading={exportMp4.isPending || p.export_status === "queued"} onClick={() => exportMp4.mutate()}>
                {p.export_status === "failed" ? t("mp4Retry") : t("mp4")}
              </Button>
            ))}
          <Button variant="secondary" loading={packing !== null} onClick={() => (packed ? void unpack(presId).then(() => setPacked(false)) : void pack())}>
            {packing ?? (packed ? t("offlineRemove") : t("offline"))}
          </Button>
        </div>
      </div>
      {packed && (
        <p role="status" className="text-sm text-ok">
          {t("offlineReady")}
        </p>
      )}
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      {p.can_edit && <Checkbox label={t("share")} checked={p.shared_with_players} onChange={(e) => share.mutate(e.target.checked)} />}

      {slides.length === 0 && <EmptyState title={t("noSlides")}>{t("noSlidesHint")}</EmptyState>}
      <ol className="space-y-2" data-testid="slides">
        {slides.map((s, i) => (
          <li
            key={s.id}
            draggable={p.can_edit}
            onDragStart={() => setDrag(s.id)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => drag && drag !== s.id && move(drag, i)}
            className={cn("bg-raised border border-border p-3", drag === s.id && "opacity-60")}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-6 text-sm text-muted tabular-nums">{i + 1}</span>
              <span className="bg-surface px-2 py-0.5 text-xs">{t(`type_${s.type}` as "type_clip")}</span>
              <span className="flex-1 font-medium">{slideTitle(s, t as never)}</span>
              {p.can_edit && (
                <>
                  <Button variant="ghost" className="min-h-8 px-2 py-1" disabled={i === 0} onClick={() => move(s.id, i - 1)} aria-label={t("up")}>
                    <ArrowUp aria-hidden />
                  </Button>
                  <Button variant="ghost" className="min-h-8 px-2 py-1" disabled={i === slides.length - 1} onClick={() => move(s.id, i + 1)} aria-label={t("down")}>
                    <ArrowDown aria-hidden />
                  </Button>
                  <Button variant="ghost" className="min-h-8 px-2 py-1" onClick={() => remove.mutate(s.id)}>
                    {t("remove")}
                  </Button>
                </>
              )}
            </div>
            {p.can_edit && s.type === "clip" && (
              <SpotlightPick
                orgId={orgId}
                videoId={String((s.content as { video_id?: string }).video_id ?? "")}
                value={((s.content as { spotlight?: number[] }).spotlight ?? [])[0] ?? null}
                onChange={(track) => patch.mutate({ id: s.id, content: { ...(s.content as object), spotlight: track == null ? [] : [track] } })}
              />
            )}
            {p.can_edit && (
              <form
                className="mt-2 flex items-end gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  patch.mutate({ id: s.id, content: { ...(s.content as object), notes: String(new FormData(e.currentTarget).get("notes") ?? "") } });
                }}
              >
                <Input label={t("notes")} name="notes" defaultValue={String((s.content as { notes?: string }).notes ?? "")} maxLength={2000} />
                <Button type="submit" variant="ghost">
                  {t("save")}
                </Button>
              </form>
            )}
          </li>
        ))}
      </ol>

      {p.can_edit && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="space-y-2">
            <h2 className="font-semibold">{t("addText")}</h2>
            <form onSubmit={addText} className="space-y-2" aria-label={t("addText")}>
              <Input label={t("slideTitle")} name="title" required maxLength={160} />
              <Input label={t("slideBody")} name="body" maxLength={2000} />
              <Button type="submit" variant="secondary">
                {t("add")}
              </Button>
            </form>
          </Card>
          <Card className="space-y-2">
            <h2 className="font-semibold">{t("addImage")}</h2>
            <form
              className="space-y-2"
              aria-label={t("addImage")}
              onSubmit={async (e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const file = f.get("image");
                if (!(file instanceof File) || file.size === 0) return;
                const slide = await add.mutateAsync({ type: "image", content: { caption: String(f.get("caption") ?? "") } });
                if (!slide) return;
                const body = new FormData();
                body.append("file", file);
                const res = await fetch(`/v1/orgs/${orgId}/slides/${slide.id}/image`, {
                  method: "PUT",
                  body,
                  credentials: "same-origin",
                  headers: { "x-csrf-token": document.cookie.match(/hb_csrf=([^;]+)/)?.[1] ?? "" },
                });
                if (!res.ok) setError(errorKey(await res.json().catch(() => null)));
                refresh();
                e.currentTarget.reset();
              }}
            >
              <FileField label={t("imageFile")} name="image" accept="image/png,image/jpeg" required button={tf("choose")} empty={tf("none")} />
              <Input label={t("caption")} name="caption" maxLength={200} />
              <Button type="submit" variant="secondary">
                {t("add")}
              </Button>
            </form>
          </Card>
          <Card className="space-y-2">
            <h2 className="font-semibold">{t("addPlay")}</h2>
            <form
              className="space-y-2"
              aria-label={t("addPlay")}
              onSubmit={(e) => {
                e.preventDefault();
                const id = String(new FormData(e.currentTarget).get("play") ?? "");
                if (id) add.mutate({ type: "tactics_board", play_id: id, content: {} });
              }}
            >
              <Select label={t("playLabel")} name="play">
                {(plays.data ?? []).map((pl) => (
                  <option key={pl.id} value={pl.id}>
                    {pl.name}
                  </option>
                ))}
              </Select>
              <Button type="submit" variant="secondary" disabled={!plays.data?.length}>
                {t("add")}
              </Button>
            </form>
            <p className="text-sm text-muted">
              {t("addClipsHint")}{" "}
              <Link className="font-medium text-accent hover:underline" href={`/app/${orgId}/teams/${p.team_id}/scenes?presentation=${presId}`}>
                {t("toSearch")}
              </Link>
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}


/** Spotlight player of a clip slide: burned into the MP4 export, drawn live when presenting. */
function SpotlightPick({ orgId, videoId, value, onChange }: { orgId: string; videoId: string; value: number | null; onChange: (track: number | null) => void }) {
  const t = useTranslations("spotlight");
  const q = useQuery({
    queryKey: ["analysis", videoId],
    enabled: Boolean(videoId),
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: orgId, video_id: videoId } } })).data ?? null,
  });
  const tracks = (q.data?.tracks ?? []).filter((tr) => tr.team && tr.team !== "referee" && tr.observed_share > 0.05);
  if (tracks.length === 0) return null;
  return (
    <div className="mt-2 max-w-xs">
      <Select label={t("title")} value={value ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}>
        <option value="">{t("off")}</option>
        {tracks.map((tr) => (
          <option key={tr.track_no} value={tr.track_no}>
            {tr.number != null ? `#${tr.number}` : t("track", { n: tr.track_no })} · {tr.team?.startsWith("home") ? t("own") : t("opponent")}
          </option>
        ))}
      </Select>
    </div>
  );
}

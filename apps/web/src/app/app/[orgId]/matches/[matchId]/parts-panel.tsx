"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { AttnTag, SectionHead, linkClass } from "@/components/anlauf/blocks";
import { Button } from "@/components/ui/button";
import { useConfirm } from "@/components/ui/confirm";
import { api } from "@/lib/client";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";
import { isShort, latestJobs, mainFiles, partName, partsOf, partStarts, partState, swappable, type PartState } from "@/lib/video-parts";

type Match = Schemas["MatchOut"];
type Job = Schemas["JobOut"];

/**
 * One match in several files (Q-VIDEO-PARTS): the halves in their order, what each is doing, and
 * the few things a coach may want: swap the order, analyse a half again, remove a file. Shown once
 * the match has more than one main file; with one file there is nothing to say.
 */
export function PartsPanel({ orgId, match, jobs, staff, onChanged }: { orgId: string; match: Match; jobs: Job[]; staff: boolean; onChanged: () => void }) {
  const t = useTranslations("parts");
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [failed, setFailed] = useState<string | null>(null);
  const path = { org_id: orgId, match_id: match.id };
  const segments = useQuery({
    queryKey: ["parts", match.id, match.videos.map((v) => `${v.id}:${v.status}:${v.part ?? ""}`).join(",")],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/parts", { params: { path } })).data ?? [],
  });
  const bounds = useQuery({
    queryKey: ["boundaries", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/boundaries", { params: { path } })).data ?? [],
  });
  const refresh = () => {
    for (const key of ["parts", "graphics", "events", "goal-candidates", "possessions", "stats"]) void qc.invalidateQueries({ queryKey: [key, match.id] });
    onChanged();
  };
  const order = useMutation({
    mutationFn: async (ids: string[]) => api.PUT("/v1/orgs/{org_id}/matches/{match_id}/parts", { params: { path }, body: { video_ids: ids } }),
    onSuccess: refresh,
  });
  const files = mainFiles(match.videos);
  const parts = partsOf(match.videos);
  const latest = latestJobs(jobs);
  const total = parts.length;
  const nameOf = (n: number) => {
    const name = partName(n, parts);
    return t(name.key, { n: name.n });
  };
  const pair = swappable(match.videos);
  const [turning, setTurning] = useState<string | null>(null);
  async function sideChange(videoId: string, value: boolean) {
    setFailed(null);
    const r = await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/parts/{video_id}/side-change", { params: { path: { ...path, video_id: videoId } }, body: { side_change: value } });
    if (r.error) setFailed(videoId);
    else setTurning(videoId);
    refresh();
  }
  const label = (v: (typeof files)[number]) => (v.part != null ? nameOf(v.part) : v.filename);
  const twinName = (id: string | null | undefined) => {
    const twin = files.find((x) => x.id === id);
    return twin?.part != null ? nameOf(twin.part) : (twin?.filename ?? "");
  };

  async function retry(videoId: string) {
    setFailed(null);
    const r = await api.POST("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: orgId, video_id: videoId } } });
    if (r.error) setFailed(videoId);
    refresh();
  }
  async function remove(v: (typeof files)[number]) {
    if (!(await confirm({ title: t("removeTitle", { name: label(v) }), body: t("removeBody"), confirm: t("remove"), danger: true }))) return;
    await api.DELETE("/v1/orgs/{org_id}/videos/{video_id}", { params: { path: { org_id: orgId, video_id: v.id } } });
    refresh();
  }

  const source = segments.data?.every((s) => s.confirmed) ? "confirmed" : segments.data?.some((s) => s.source === "metadata") ? "orderMetadata" : "orderUpload";
  const gapOf = (id: string) => segments.data?.find((s) => s.video_id === id)?.gap_before_ms ?? null;
  if (files.length < 2 && (bounds.data ?? []).length === 0) return null;
  return (
    <section className="space-y-3" data-testid="parts" aria-label={t("title", { n: files.length })}>
      {files.length > 1 && (
        <>
          <SectionHead
            title={t("title", { n: total > 1 ? total : files.length })}
            note={total > 1 ? t(source) : undefined}
            action={
              staff && pair ? (
                <button
                  type="button"
                  className={cn(linkClass, "min-h-11 cursor-pointer border-0 bg-transparent p-0")}
                  disabled={order.isPending}
                  onClick={() => order.mutate(parts.map((x) => (x.id === pair[0].id ? pair[1].id : x.id === pair[1].id ? pair[0].id : x.id)))}
                  data-testid="parts-swap"
                >
                  {t("swap")}
                </button>
              ) : undefined
            }
          />
          <ol className="m-0 list-none p-0">
            {files.map((v) => {
              const st = partState(v, latest);
              const short = isShort(v, files) && st.kind !== "duplicate";
              const gap = v.part != null && v.part > 1 ? gapOf(v.id) : null;
              const seg = segments.data?.find((x) => x.video_id === v.id);
              // a later part: whether the teams changed ends before it, one tap to say otherwise
              const askTurn = staff && seg != null && v.part != null && v.part > 1 && !short && st.kind !== "duplicate";
              return (
                <li key={v.id} className="grid gap-x-4 gap-y-1.5 border-b border-rule py-3 sm:grid-cols-[minmax(0,1fr)_auto]" data-testid="part-row" data-state={st.kind}>
                  <div className="min-w-0 space-y-1">
                    <p className="m-0 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <span className="font-slant text-[20px] leading-none">{label(v)}</span>
                      {v.duration_s != null && <span className="text-[15px] tabular-nums text-ink-2">{t("length", { time: formatClock(v.duration_s * 1000) })}</span>}
                      {gap != null && gap > 5000 && <span className="text-[15px] text-ink-2">{t("gap", { time: formatClock(gap) })}</span>}
                    </p>
                    {v.part != null && <p className="m-0 truncate text-[15px] text-ink-2">{v.filename}</p>}
                    <State st={st} />
                    {st.kind === "analysisFailed" && <p className="m-0 max-w-[60ch] text-[15px]">{t("failedNote", { name: label(v) })}</p>}
                    {st.kind === "duplicate" && <p className="m-0 max-w-[60ch] text-[15px]">{t("duplicateNote", { name: twinName(v.duplicate_of) })}</p>}
                    {short && (
                      <p className="m-0 max-w-[60ch] text-[15px]" data-testid="part-short">
                        <AttnTag>{t("short", { seconds: Math.round(v.duration_s ?? 0) })}</AttnTag>
                      </p>
                    )}
                    {askTurn && (
                      <p className="m-0 flex flex-wrap items-center gap-x-3 text-[15px] text-ink-2" data-testid="part-side-change">
                        <span>{t("sideChange")}</span>
                        {[true, false].map((value) =>
                          seg.side_change_assumed === value ? (
                            <span key={String(value)} className="font-bold text-ink" aria-current="true">
                              {value ? t("yes") : t("no")}
                            </span>
                          ) : (
                            <button
                              key={String(value)}
                              type="button"
                              className={cn(linkClass, "min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[15px]")}
                              disabled={st.kind === "analysing" || st.kind === "processing"}
                              onClick={() => void sideChange(v.id, value)}
                              data-testid={`part-side-change-${value ? "yes" : "no"}`}
                            >
                              {value ? t("yes") : t("no")}
                            </button>
                          ),
                        )}
                      </p>
                    )}
                    {turning === v.id && <p className="m-0 max-w-[60ch] text-[15px]">{t("sideChangeRerun", { name: label(v) })}</p>}
                    {failed === v.id && <p className="m-0 text-[15px] font-bold" role="alert">{t("state_analysisFailed")}</p>}
                  </div>
                  {staff && (
                    <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                      {(st.kind === "analysisFailed" || st.kind === "notAnalysed") && (
                        <Button size="sm" onClick={() => void retry(v.id)} data-testid="part-retry">
                          {st.kind === "analysisFailed" ? t("retry") : t("analyse")}
                        </Button>
                      )}
                      {total > 2 && v.part != null && v.part > 1 && !short && (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={order.isPending}
                          onClick={() => {
                            const ids = parts.map((x) => x.id);
                            const k = ids.indexOf(v.id);
                            [ids[k - 1], ids[k]] = [ids[k]!, ids[k - 1]!];
                            order.mutate(ids);
                          }}
                        >
                          {t("up")}
                        </Button>
                      )}
                      <Button size="sm" variant={short || st.kind === "duplicate" ? "primary" : "secondary"} onClick={() => void remove(v)} data-testid="part-remove" aria-label={`${t("remove")}: ${label(v)}`}>
                        {t("remove")}
                      </Button>
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </>
      )}
      {(bounds.data ?? []).map((b) => (
        <p key={`${b.video_id}-${b.t_ms}`} className="m-0 max-w-[60ch] border-l-4 border-attn pl-3 text-[15px]">
          {t("boundary", { time: formatClock(b.t_ms), pause: Math.round((b.pause_ms ?? 0) / 60000) })}
        </p>
      ))}
    </section>
  );
}

function State({ st }: { st: PartState }) {
  const t = useTranslations("parts");
  const text = st.kind === "analysing" ? t("state_analysing", { percent: Math.floor(st.progress * 100) }) : t(`state_${st.kind}`);
  if (st.kind === "ready")
    return (
      <p className="m-0 inline-flex items-center gap-1.5 text-[15px] font-bold text-win">
        <Check aria-hidden className="size-4" />
        {text}
      </p>
    );
  // the word carries an error, not a colour (ANLAUF 4)
  return <p className="m-0 text-[15px] font-bold text-ink">{text}</p>;
}

/** Markers on the player's bar where each further part starts (the line between the halves). */
export function usePartMarkers(videos: Match["videos"]): { t_ms: number; kind: "part"; label: string }[] {
  const t = useTranslations("parts");
  const parts = partsOf(videos);
  const starts = partStarts(videos);
  const sig = starts.map((p) => `${p.part}:${p.start_ms}:${parts.find((x) => x.part === p.part)?.half ?? ""}`).join(",");
  return useMemo(
    () =>
      starts.map((p) => {
        const name = partName(p.part, parts);
        return { t_ms: p.start_ms, kind: "part" as const, label: t("marker", { name: t(name.key, { n: name.n }) }) };
      }),
    [sig, t], // eslint-disable-line react-hooks/exhaustive-deps
  );
}

/** Under the match video of several parts: that it shows them one after the other, and a jump to
 * the start of each further part. */
export function PartsLine({ videos, onJump }: { videos: Match["videos"]; onJump: (ms: number) => void }) {
  const t = useTranslations("parts");
  const parts = partsOf(videos);
  const starts = partStarts(videos);
  if (parts.length < 2 || starts.length === 0) return null;
  return (
    <p className="m-0 flex max-w-[66ch] flex-wrap items-center gap-x-4 gap-y-1 text-[17px]" data-testid="parts-line">
      <span>{parts.length === 2 ? (parts.every((p) => p.half != null) ? t("videoBoth") : t("videoTwo")) : t("videoAll", { n: parts.length })}</span>
      {starts.map((p) => {
        const name = partName(p.part, parts);
        return (
          <button key={p.video_id} type="button" onClick={() => onJump(p.start_ms)} className={cn(linkClass, "min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[17px]")} data-testid="parts-jump">
            {name.key === "half" ? t("jump", { name: t("half", { n: name.n }) }) : t("jumpPart", { n: p.part })}
          </button>
        );
      })}
    </p>
  );
}

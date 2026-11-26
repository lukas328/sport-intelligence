"use client";

import { ChevronRight, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useNow, useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useConfirm } from "@/components/ui/confirm";
import { api } from "@/lib/client";
import { dismissedUploads, dismissUploads, isActive, markSeen, onlyDismissed, progressKey, seenDone, tone, useProgress, withLocal, type MatchProgress } from "@/lib/progress";
import { stopLocalUpload } from "@/lib/upload-store";
import { useLocalUploads } from "@/lib/upload-store";
import { useStoredUploads } from "./words";
import { cn } from "@/lib/utils";
import { useProgressWords } from "./words";

/**
 * The upload or analysis of the club, in one line under the top bar of every page (K6, K13):
 * what runs, how far, until when; a tap opens the match. Stalled or stopped work says so in the
 * attention colour; a finished one stays until opened or closed. Nothing while nothing runs, and
 * not for the match whose page is open (its own block says more there).
 */
export function ProgressStrip({ orgId }: { orgId: string }) {
  const path = usePathname();
  const local = useLocalUploads();
  const stored = useStoredUploads(local);
  const q = useProgress(orgId);
  const now = useNow({ updateInterval: 15_000 }).getTime();
  const w = useProgressWords();
  const t = useTranslations("progress");
  const [seen, setSeen] = useState<Set<string> | null>(null);
  useEffect(() => setSeen(seenDone()), []);
  // stopped uploads whose line the coach dismissed (A9)
  const [dismissed, setDismissed] = useState<Set<string>>(() => new Set());
  useEffect(() => setDismissed(dismissedUploads()), []);
  const confirm = useConfirm();
  const qc = useQueryClient();
  // an upload of this tab the list does not know yet: ask again (it is there after the first part)
  const unknown = local.some((u) => u.videoId && !(q.data ?? []).some((p) => p.match_id === u.matchId));
  useEffect(() => {
    if (unknown) void q.refetch();
  }, [unknown]); // eslint-disable-line react-hooks/exhaustive-deps

  const items = useMemo(() => {
    const all = withLocal(q.data ?? [], local, now, stored);
    return all.filter((p) => !path.includes(`/matches/${p.match_id}`) && !onlyDismissed(p, dismissed) && (isActive(p) || (seen != null && !seen.has(p.match_id))));
  }, [q.data, local, now, path, seen, stored, dismissed]);
  if (!items.length) return null;
  const p: MatchProgress = items[0]!;
  const tn = tone(p);
  const when = w.when(p, now);
  const close = () => {
    markSeen(p.match_id);
    setSeen(seenDone());
  };
  // «Verwerfen»: the line goes at once; then the offer to cancel the stopped upload as well
  const discard = async () => {
    const ids = p.files.filter((f) => f.state === "interrupted").map((f) => f.video_id);
    dismissUploads(ids);
    setDismissed(dismissedUploads());
    const cancel = await confirm({ title: t("discardTitle"), body: t("discardBody", { name: w.matchName(p) }), confirm: t("cancelUpload"), cancel: t("discardKeep"), danger: true });
    if (!cancel) return;
    for (const id of ids) {
      stopLocalUpload(id);
      await api.DELETE("/v1/orgs/{org_id}/videos/{video_id}", { params: { path: { org_id: orgId, video_id: id } } });
    }
    void qc.invalidateQueries({ queryKey: progressKey(orgId) });
    void qc.invalidateQueries({ queryKey: ["match"] });
  };
  const detail = [
    isActive(p) && p.state !== "interrupted" && p.state !== "stalled" ? w.percent(p.overall) : null,
    p.state === "stalled" ? t("silentFor", { m: Math.round(Math.max(...p.files.map((f) => f.idle_s ?? 0)) / 60) }) : null,
    p.state === "interrupted" ? t("stripInterrupted") : null,
    when,
    items.length > 1 ? t("stripMore", { n: items.length - 1 }) : null,
  ].filter(Boolean);
  // the hall image of a running analysis is there: marking the court now completes it in one run
  // (#141); the link opens the marking on the match
  const courtMark = isActive(p) && p.files.some((f) => f.court === "mark");
  // on a phone one part: what needs a look, else the time, else how far
  const phone = p.state === "stalled" || p.state === "interrupted" ? detail[0] : isActive(p) ? (when ?? w.percent(p.overall)) : null;
  return (
    <div
      className={cn(
        "relative border-t-2 border-ink",
        tn === "attn" ? "bg-attn text-attn-ink" : tn === "fail" ? "bg-paper text-loss" : "bg-paper text-ink",
      )}
      data-testid="progress-strip"
      data-state={p.state}
    >
      {/* the whole way, as a band under the line */}
      {isActive(p) && tn === "run" && (
        <span aria-hidden className="absolute bottom-0 left-0 h-[3px] bg-ink transition-[width] duration-700" style={{ width: `${Math.max(2, p.overall * 100)}%` }} />
      )}
      <div className="mx-auto flex min-h-11 max-w-[1440px] items-center gap-2 px-4 md:px-8">
        <Link
          href={`/app/${orgId}/matches/${p.match_id}`}
          className="flex min-h-11 min-w-0 flex-1 items-center gap-2 text-[15px] text-inherit no-underline"
          aria-live="polite"
          onClick={() => !isActive(p) && close()}
        >
          {/* two lines on a phone: the finish time is the point and must not be cut off */}
          <span className="min-w-0 flex-1 leading-snug max-sm:line-clamp-2 sm:truncate">
            <b className="font-bold">{w.headline(p).endsWith("?") ? w.headline(p) : `${w.headline(p)}:`}</b> {w.matchName(p)}
            {detail.length > 0 && <span className="max-sm:hidden"> · {detail.join(" · ")}</span>}
            {/* on a phone the time comes in a second short part, the rest is in the match */}
            {phone && <span className="sm:hidden"> · {phone}</span>}
          </span>
          {!courtMark && <span className="shrink-0 font-bold underline decoration-[1.5px] underline-offset-4 max-[389px]:sr-only">{t("stripOpen")}</span>}
          {!courtMark && <ChevronRight aria-hidden className="size-4 shrink-0" />}
        </Link>
        {courtMark && (
          <Link
            href={`/app/${orgId}/matches/${p.match_id}?tab=video&mark=court`}
            className="flex min-h-11 shrink-0 items-center gap-1 bg-attn px-2 text-[15px] font-bold text-attn-ink no-underline"
            data-testid="strip-court"
          >
            {t("stripCourt")}
            <ChevronRight aria-hidden className="size-4 shrink-0" />
          </Link>
        )}
        {p.state === "interrupted" && (
          <button type="button" onClick={() => void discard()} className="min-h-11 shrink-0 cursor-pointer border-0 bg-transparent px-1 text-[15px] font-bold text-inherit underline decoration-[1.5px] underline-offset-4" data-testid="strip-discard">
            {t("discard")}
          </button>
        )}
        {!isActive(p) && (
          <button type="button" onClick={close} className="grid size-11 shrink-0 cursor-pointer place-items-center border-0 bg-transparent text-inherit" aria-label={t("stripClose")}>
            <X aria-hidden className="size-4" />
          </button>
        )}
      </div>
    </div>
  );
}

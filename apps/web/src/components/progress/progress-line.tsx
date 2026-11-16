"use client";

import { useNow, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { isActive, tone, useProgress, withLocal } from "@/lib/progress";
import { useLocalUploads } from "@/lib/upload-store";
import { cn } from "@/lib/utils";
import { useProgressWords } from "./words";

/**
 * The progress of one match in a line (Spiele, K6): «Analyse läuft · 42 % · fertig etwa um 20:15»,
 * with a thin bar. Null when nothing runs for the match (the caller shows its usual line).
 */
export function ProgressLine({ orgId, matchId, bar = true, className, fallback = null }: { orgId: string; matchId: string; bar?: boolean; className?: string; fallback?: ReactNode }) {
  const q = useProgress(orgId);
  const local = useLocalUploads();
  const now = useNow({ updateInterval: 15_000 }).getTime();
  const w = useProgressWords();
  const t = useTranslations("progress");
  const p = withLocal((q.data ?? []).filter((x) => x.match_id === matchId), local, now)[0];
  if (!p || !isActive(p)) return <>{fallback}</>;
  const tn = tone(p);
  const when = w.when(p, now);
  const parts = [
    w.headline(p),
    p.state === "stalled" ? t("silentFor", { m: Math.round(Math.max(...p.files.map((f) => f.idle_s ?? 0)) / 60) }) : p.state === "interrupted" ? t("stripInterrupted") : w.percent(p.overall),
    p.state === "running" ? when : null,
  ].filter(Boolean);
  return (
    <span className={cn("block", className)} data-testid="progress-line" data-state={p.state}>
      <span className={cn(tn === "attn" && "bg-attn px-1 font-bold text-attn-ink")}>{parts.join(" · ")}</span>
      {bar && tn === "run" && (
        <span aria-hidden className="mt-1 block h-1 max-w-56 bg-rule">
          <span className="block h-full bg-ink transition-[width] duration-700" style={{ width: `${Math.max(3, p.overall * 100)}%` }} />
        </span>
      )}
    </span>
  );
}

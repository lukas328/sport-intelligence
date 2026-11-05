"use client";

import { Play } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";
import { useGameTime } from "./game-time";

/** Coach overview of "Deine Szenen" (addendum 01, 4.7): scenes, comments, self-assessments. */
export function TeamFeedView({
  orgId,
  matchId,
  onPlay,
  kickoff,
  periodS,
  compact = false,
}: {
  orgId: string;
  matchId: string;
  onPlay?: ((ms: number) => void) | undefined;
  kickoff?: Record<string, number> | null;
  periodS: number;
  /** beside the player in the workspace: one column */
  compact?: boolean;
}) {
  const t = useTranslations("feed");
  const { at } = useGameTime(kickoff, periodS);
  const qc = useQueryClient();
  const path = { org_id: orgId, match_id: matchId };
  const key = ["team-feed", matchId];
  const [msg, setMsg] = useState<string | null>(null);
  const q = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/feed", { params: { path } })).data ?? [],
  });
  const generate = useMutation({
    mutationFn: async () => (await api.POST("/v1/orgs/{org_id}/matches/{match_id}/feed/generate", { params: { path } })).data,
    onSuccess: (d) => {
      setMsg(t("generated", { n: d?.players ?? 0 }));
      void qc.invalidateQueries({ queryKey: key });
    },
  });
  const comment = useMutation({
    mutationFn: async ({ id, text }: { id: string; text: string }) =>
      api.PATCH("/v1/orgs/{org_id}/feed-items/{item_id}", { params: { path: { org_id: orgId, item_id: id } }, body: { coach_comment: text || null } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: key }),
  });
  // squad order, as on the match sheet
  const players = [...(q.data ?? [])].sort((a, b) => (a.number ?? 99) - (b.number ?? 99));
  const scenes = players.reduce((n, p) => n + p.items.length, 0);
  const waiting = players.filter((p) => !p.self_assessment).length;
  const noted = (p: (typeof players)[number]) => p.items.filter((s) => s.coach_comment).length;
  const done = players.reduce((n, p) => n + noted(p), 0);
  // the coach's queue: the next player without a note carries the signal
  const next = players.find((p) => p.items.length > 0 && noted(p) === 0);
  return (
    <section className="space-y-5" aria-labelledby="feed-overview">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-foreground/15 pb-3">
        <div className="space-y-1">
          <h2 id="feed-overview" className={compact ? "sr-only" : "font-display text-2xl"}>
            {t("overview")}
          </h2>
          {players.length > 0 && (
            <p className="font-score text-lg tabular-nums" data-testid="feed-progress">
              {t("progress", { done, total: scenes })}
              {next && (
                <>
                  {" · "}
                  {t("nextUp")}{" "}
                  <span>{next.name}</span>
                </>
              )}
            </p>
          )}
          <p className="text-sm text-muted">
            {players.length > 0 && `${t("summary", { players: players.length, waiting })} `}
            {t("overviewIntro")}{" "}
            <span className="whitespace-nowrap">
              <span aria-hidden className="mr-1 inline-block size-2 rounded-full bg-foreground align-middle" />
              {t("positive")}
              <span aria-hidden className="mr-1 ml-3 inline-block size-2 rounded-full ring-[1.5px] ring-inset ring-foreground align-middle" />
              {t("toLearn")}
            </span>
          </p>
        </div>
        <Button variant="secondary" size="sm" loading={generate.isPending} onClick={() => generate.mutate()}>
          {t("generate")}
        </Button>
      </div>
      {msg && (
        <p role="status" className="text-sm">
          {msg}
        </p>
      )}
      {q.data && q.data.length === 0 && <EmptyState title={t("noFeed")} />}
      {/* one block per player, like a match sheet: who, how they rated themselves, their scenes */}
      <div className={cn("grid gap-x-12 gap-y-8", !compact && "lg:grid-cols-2")}>
        {players.map((p) => (
          <div key={p.player_id} className="space-y-1" data-testid="feed-player">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 border-b-2 border-foreground pb-1">
              <h3 className="font-semibold">
                {p.number != null && <span className="mr-1.5 font-score text-accent tabular-nums">{p.number}</span>}
                <span className={cn(p === next && "underline decoration-resin decoration-[5px] underline-offset-[5px]")}>{p.name}</span>
              </h3>
              <p className="text-sm text-muted">
                {p.self_assessment && (
                  <span className="mr-3">
                    {t("selfShort")} <span className="font-score text-foreground tabular-nums">{p.self_assessment.rating}/5</span>
                  </span>
                )}
                <span className="font-score tabular-nums">{t("notesOf", { n: noted(p), m: p.items.length })}</span>
              </p>
            </div>
            <ol>
              {/* in match order, as the coach will watch them */}
              {[...p.items].sort((a, b) => a.start_ms - b.start_ms).map((s) => (
                <Scene
                  key={s.id}
                  label={t(`reason_${s.reason}` as "reason_goal")}
                  positive={s.positive}
                  seen={s.seen}
                  // the scene starts 6 s before the moment (the API's lead-in)
                  time={at(s.start_ms + 6000)}
                  note={s.coach_comment ?? null}
                  onPlay={onPlay ? () => onPlay(s.start_ms) : undefined}
                  onSave={(text) => comment.mutate({ id: s.id, text })}
                />
              ))}
            </ol>
          </div>
        ))}
      </div>
    </section>
  );
}

/** One scene: match clock, what happened, play; a coach note opens on request and reads like a
 * note in the margin of the match sheet. */
function Scene({
  label,
  positive,
  seen,
  time,
  note,
  onPlay,
  onSave,
}: {
  label: string;
  positive: boolean;
  seen: boolean;
  time: string;
  note: string | null;
  onPlay?: (() => void) | undefined;
  onSave: (text: string) => void;
}) {
  const t = useTranslations("feed");
  const [editing, setEditing] = useState(false);
  return (
    <li className="group border-b border-border/70 py-1.5 text-sm">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {onPlay ? (
          <Button variant="quiet" size="sm" className="font-score tabular-nums" aria-label={t("play", { what: label, time })} onClick={onPlay}>
            <Play aria-hidden className="size-3 fill-current" />
            {time}
          </Button>
        ) : (
          <span className="px-2 font-score tabular-nums">{time}</span>
        )}
        <span className="flex min-w-0 flex-1 items-center gap-2">
          {/* filled: positive, ring: to learn from (not colour alone) */}
          <span aria-hidden className={cn("size-2 shrink-0 rounded-full", positive ? "bg-foreground" : "ring-[1.5px] ring-inset ring-foreground")} />
          <span>{label}</span>
          <span className="sr-only">{positive ? t("positive") : t("toLearn")}</span>
          {seen && <span className="text-xs text-muted">{t("seen")}</span>}
        </span>
        {!editing && (
          <Button variant="ghost" size="sm" className={cn(!note && "pointer-fine:opacity-0 pointer-fine:group-hover:opacity-100 pointer-fine:focus-visible:opacity-100")} onClick={() => setEditing(true)}>
            {note ? t("editNote") : t("addNote")}
          </Button>
        )}
      </div>
      {note && !editing && <p className="pl-2 pt-0.5 font-hand text-2xl leading-none text-foreground/85">{note}</p>}
      {editing && (
        <form
          className="flex items-end gap-2 pt-1.5"
          onSubmit={(e) => {
            e.preventDefault();
            onSave(String(new FormData(e.currentTarget).get("c") ?? "").trim());
            setEditing(false);
          }}
          onKeyDown={(e) => e.key === "Escape" && setEditing(false)}
        >
          <Input label={t("comment")} name="c" defaultValue={note ?? ""} maxLength={1000} autoFocus />
          <Button type="submit" variant="secondary" size="sm">
            {t("saveComment")}
          </Button>
        </form>
      )}
    </li>
  );
}

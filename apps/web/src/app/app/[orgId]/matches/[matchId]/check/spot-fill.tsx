"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type CSSProperties, useEffect, useRef, useState } from "react";
import { Strip } from "@/components/anlauf/heads";
import { ShotSpotPicker } from "@/components/anlauf/shot-spot-picker";
import { useSaveSpot } from "@/components/anlauf/spot-parts";
import { clockOf } from "@/components/anlauf/three-things-view";
import { useShell } from "@/components/shell/context";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import { matchStyle } from "@/lib/color";
import { formatClock } from "@/lib/format";
import { goalWindow } from "@/lib/goal-window";
import { type MatchGraphics, useMatchGraphics } from "@/lib/graphics";
import { useOpponentName } from "@/lib/opponent";
import { ownName } from "@/lib/own-name";
import { goalsWithoutSpot, type SpotZone } from "@/lib/shot-spot";
import { cn } from "@/lib/utils";
import { timelineVideo } from "@/lib/video-parts";

type Match = Schemas["MatchOut"];
type Goal = MatchGraphics["goals"][number];

/**
 * «Wurfort nachtragen» (fourth real-video test H7): goals already confirmed without the place of
 * the shot (older matches, goals of the match report once the throw-off puts them in the video),
 * one after the other, only «Von wo?», with a count «3 von 9» and «Später weiter». The video plays
 * each goal's moment on the match timeline: a goal of the second half from the second file.
 * `goalId`: only that goal (from a scene).
 */
export function SpotFill({ orgId, match, goalId }: { orgId: string; match: Match; goalId?: string | null }) {
  const t = useTranslations("spot");
  const tc = useTranslations("check");
  const ta = useTranslations("anlauf");
  const { org, teams } = useShell();
  const own = ownName(teams.find((x) => x.id === match.team_id)?.name, org.name);
  const oppName = useOpponentName()(match);
  const graphics = useMatchGraphics(orgId, match.id);
  const save = useSaveSpot(orgId, match.id);
  const main = timelineVideo(match.videos) ?? null;
  // the goals taken once when the screen opens, so answering does not shuffle the count
  const [list, setList] = useState<Goal[] | null>(null);
  useEffect(() => {
    if (list || !graphics.data) return;
    const g = graphics.data;
    setList(goalId ? g.goals.filter((x) => x.event_id === goalId && x.t_ms != null) : goalsWithoutSpot(g));
  }, [list, graphics.data, goalId]);
  const [at, setAt] = useState(0);
  const [failed, setFailed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [unknown, setUnknown] = useState(0);
  const player = useRef<PlayerHandle>(null);
  const back = `/app/${orgId}/matches/${match.id}`;
  const goal = list?.[at] ?? null;
  const total = list?.length ?? 0;
  const who = (g: Goal) => t("fillGoal", { team: g.team === "own" ? own : oppName });
  const when = (g: Goal) => (g.minute != null ? `${clockOf(g.minute)} · ${tc("videoAt", { video: formatClock(g.t_ms ?? 0) })}` : tc("videoAt", { video: formatClock(g.t_ms ?? 0) }));
  // keyboard and screen reader: each goal's question takes the focus
  useEffect(() => {
    if (at === 0) return;
    window.scrollTo({ top: 0 });
    document.getElementById("spot-fill-question")?.focus({ preventScroll: true });
  }, [at]);
  const media = main ? `/v1/orgs/${orgId}/videos/${main.id}/media/hls/master.m3u8` : null;

  return (
    <div style={matchStyle([org.primary_color, org.secondary_color ?? null], match.opponent_colors ? [match.opponent_colors.color, match.opponent_colors.second ?? null] : null) as CSSProperties} data-testid="spot-fill-view">
      <div className="bleed-x -mt-px flex h-[60px] items-center justify-between gap-3 border-b-2 border-ink px-4 md:px-8">
        <span className="min-w-0 truncate text-[15px] font-bold">{t("fillTop", { opponent: `${own} ${ta("vsShort")} ${oppName}` })}</span>
        <Link href={back} className="inline-flex min-h-11 shrink-0 items-center border-2 border-ink px-3.5 text-[15px] font-bold whitespace-nowrap text-ink no-underline">
          {tc("later")}
        </Link>
      </div>
      {/* on a phone video and court share one screen: the strip gives way */}
      <div className="bleed-x max-md:hidden">
        <Strip name={own} sub={`${ta("vsShort")} ${oppName}${goal ? ` · ${t("fillCount", { n: at + 1, total })}` : ""}`} own={match.score_own} opp={match.score_opponent} />
      </div>
      {!list ? (
        <p className="py-10 text-ink-2">{tc("loading")}</p>
      ) : !goal ? (
        <div className="max-w-[60ch] space-y-4 py-10" data-testid="spot-fill-done">
          <h1 className="text-[40px] md:text-[58px]">{total === 0 ? t("fillNone") : unknown > 0 ? tc("roundDone") : t("fillDone")}</h1>
          {total > 0 && <p className="text-[17px] text-ink-2">{t("fillDoneText")}</p>}
          <Link href={back} className="inline-flex min-h-12 items-center border-2 border-ink bg-ink px-5 font-bold text-ground no-underline" data-testid="spot-fill-to-match">
            {tc("toMatch")}
          </Link>
        </div>
      ) : (
        <div className="grid gap-2 py-2 md:grid-cols-[minmax(0,1fr)_420px] md:gap-14 md:py-10">
          <figure className="relative m-0 self-start bg-court-bar">
            {media && goal.t_ms != null && <VideoPlayer ref={player} key={goal.event_id} src={media} window={goalWindow({ t_ms: goal.t_ms })} autoPlay bare />}
            <figcaption className="flex flex-wrap max-md:hidden items-center justify-between gap-x-3 gap-y-1 bg-court-bar px-3 py-1.5 text-court-text">
              <span className="font-mono text-[13px] font-semibold">{when(goal)}</span>
              <button
                type="button"
                onClick={() => {
                  player.current?.seek(goalWindow({ t_ms: goal.t_ms ?? 0 }).start_ms);
                  player.current?.play();
                }}
                className="min-h-11 cursor-pointer border-[1.5px] border-court-text bg-transparent px-3 text-[15px] font-bold text-white"
                data-testid="check-replay"
              >
                {t("replay")}
              </button>
            </figcaption>
          </figure>
          <section aria-labelledby="spot-fill-question" data-testid="spot-step">
            <p className="m-0 text-[15px] font-semibold md:text-[17px]">
              <span className="text-ink-2">{t("fillCount", { n: at + 1, total })}</span> · {who(goal)} <span className="font-mono text-[13px] text-ink-2 md:hidden">{when(goal)}</span>
            </p>
            <div className="flex items-end justify-between gap-3">
              <h1 id="spot-fill-question" tabIndex={-1} className="mt-1 mb-0 text-[32px] leading-[.95] outline-none md:mt-2 md:text-[58px]">
                {t("question")}
              </h1>
              <button
                type="button"
                onClick={() => {
                  player.current?.seek(goalWindow({ t_ms: goal.t_ms ?? 0 }).start_ms);
                  player.current?.play();
                }}
                className="min-h-11 shrink-0 cursor-pointer border-2 border-ink bg-transparent px-3 text-[15px] font-bold text-ink md:hidden"
                data-testid="spot-replay"
              >
                {t("replay")}
              </button>
            </div>
            <p className="mt-1 mb-0 max-w-[54ch] text-[15px] text-ink-2 md:mt-3 md:text-[17px]">
              {t("why")} {goal.zone_source === "estimated" ? t("suggestedWhy") : ""}
            </p>
            {failed && (
              <p role="alert" className="mt-4 max-w-[54ch] border-l-4 border-loss pl-3 text-[17px] font-semibold" data-testid="check-failed">
                {tc("saveFailed")} <span className="block text-[15px] font-normal text-ink-2">{failed}</span>
              </p>
            )}
            <div className="mt-2 md:mt-4">
              <ShotSpotPicker
                key={goal.event_id}
                disabled={busy}
                suggestion={goal.zone ? { zone: goal.zone as SpotZone, kind: goal.zone_source === "estimated" ? "estimated" : "current" } : null}
                onPick={(spot, point) => {
                  setBusy(true);
                  setFailed(null);
                  save(goal.event_id, spot, point)
                    .then(() => {
                      if (spot === "unknown") setUnknown((n) => n + 1);
                      setAt((n) => n + 1);
                    })
                    .catch((e: unknown) => setFailed(e instanceof Error ? e.message : String(e)))
                    .finally(() => setBusy(false));
                }}
              />
            </div>
            <div className="mt-7 flex gap-[3px]" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={at} aria-label={t("fillCount", { n: at, total })}>
              {list.map((g, i) => (
                <i key={g.event_id} className={cn("block h-1.5 flex-1", i < at ? "bg-ink" : "bg-rule")} />
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

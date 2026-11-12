"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type CSSProperties, useCallback, useEffect, useMemo, useState } from "react";
import { Strip } from "@/components/anlauf/heads";
import { useShell } from "@/components/shell/context";
import { VideoPlayer } from "@/components/video/player";
import { api } from "@/lib/client";
import { matchStyle } from "@/lib/color";
import { useOpponentName } from "@/lib/opponent";
import { cn } from "@/lib/utils";

type Match = Schemas["MatchOut"];
type Candidate = Schemas["GoalCandidateRow"];

type Question = { kind: "field"; videoId: string } | { kind: "goal"; c: Candidate };
type Answer = { key: string; label: string; first?: boolean; numeral?: string; run: () => Promise<void> };

const clock = (s: number | null | undefined) => (s == null ? "" : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`);

/**
 * Prüfen (SPEC 7.5): the questions the analysis cannot answer itself, one at a time. The court
 * first (until it is confirmed there are no positions), then the goal candidates. A question
 * about a person needs a box in the picture, which the analysis does not deliver yet: not asked
 * (OPEN_QUESTIONS Q-UX-20). Every answer is saved at once; the screen can be left at any time.
 */
export function CheckView({ orgId, match }: { orgId: string; match: Match }) {
  const t = useTranslations("check");
  const ta = useTranslations("anlauf");
  const qc = useQueryClient();
  const { org } = useShell();
  const oppName = useOpponentName()(match);
  const main = match.videos.find((v) => v.role === "main" && v.status === "ready") ?? null;
  const path = { org_id: orgId, match_id: match.id };
  const analysis = useQuery({
    queryKey: ["analysis", main?.id],
    enabled: main != null,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: orgId, video_id: main!.id } } })).data ?? null,
  });
  const candidates = useQuery({
    queryKey: ["goal-candidates", match.id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/matches/{match_id}/goal-candidates", { params: { path, query: { kind: "goal" } } })).data ?? null,
  });
  const [done, setDone] = useState<string[]>([]);
  const questions = useMemo<Question[]>(() => {
    const q: Question[] = [];
    const cal = analysis.data?.calibration;
    if (main && analysis.data?.status === "ready" && (!cal || cal.source !== "user_correction")) q.push({ kind: "field", videoId: main.id });
    for (const c of candidates.data?.candidates ?? []) if (c.status === "open") q.push({ kind: "goal", c });
    return q;
  }, [analysis.data, candidates.data, main]);
  const open = questions.filter((q) => !done.includes(id(q)));
  const current = open[0] ?? null;
  const total = questions.length;
  const next = useCallback((q: Question) => setDone((d) => [...d, id(q)]), []);

  const answers: Answer[] = !current
    ? []
    : current.kind === "field"
      ? [
          {
            key: "1",
            label: t("fieldYes"),
            first: true,
            run: async () => {
              await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/confirm", { params: { path: { org_id: orgId, video_id: current.videoId } } });
              void qc.invalidateQueries({ queryKey: ["analysis"] });
              void qc.invalidateQueries({ queryKey: ["graphics", match.id] });
            },
          },
          { key: "2", label: t("fieldCorners"), run: async () => void (window.location.href = `/app/${orgId}/matches/${match.id}?tab=video`) },
        ]
      : [
          {
            key: "1",
            label: t("goalOf", { team: org.name }),
            numeral: "1",
            first: current.c.suggested_side !== "opponent",
            run: () => review(current.c, { status: "confirmed", side: "own", outcome: "goal" }),
          },
          {
            key: "2",
            label: t("goalOf", { team: oppName }),
            numeral: "2",
            first: current.c.suggested_side === "opponent",
            run: () => review(current.c, { status: "confirmed", side: "opponent", outcome: "goal" }),
          },
          { key: "3", label: t("noGoal"), numeral: "3", run: () => review(current.c, { status: "rejected" }) },
        ];

  async function review(c: Candidate, body: Schemas["GoalCandidateReviewIn"]) {
    await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/goal-candidates/{candidate_id}/review", { params: { path: { ...path, candidate_id: c.id } }, body });
    void qc.invalidateQueries({ queryKey: ["graphics", match.id] });
  }

  async function answer(a: Answer) {
    if (!current) return;
    await a.run();
    next(current);
  }

  // keys 1 to 3 answer, 0 is «Weiss nicht» (desktop)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!current || e.metaKey || e.ctrlKey || (e.target as HTMLElement)?.closest("input, textarea")) return;
      const a = answers.find((x) => x.key === e.key);
      if (a) void answer(a);
      else if (e.key === "0") next(current);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const media = main ? `/v1/orgs/${orgId}/videos/${main.id}/media` : null;
  const back = `/app/${orgId}/matches/${match.id}`;
  const loading = candidates.isLoading || (main != null && analysis.isLoading);
  return (
    <div style={matchStyle([org.primary_color, org.secondary_color ?? null], match.opponent_colors ? [match.opponent_colors.color, match.opponent_colors.second ?? null] : null) as CSSProperties} data-testid="check">
      <div className="bleed-x -mt-px flex h-[60px] items-center justify-between gap-3 border-b-2 border-ink px-4 md:px-8">
        <span className="text-[15px] font-bold">{t("top", { opponent: `${org.name} ${ta("vsShort")} ${oppName}` })}</span>
        <Link href={back} className="inline-flex min-h-11 items-center border-2 border-ink px-3.5 text-[15px] font-bold text-ink no-underline">
          {t("later")}
        </Link>
      </div>
      <div className="bleed-x">
        <Strip name={org.name} sub={`${ta("vsShort")} ${oppName} · ${t("count", { n: total })}`} own={match.score_own} opp={match.score_opponent} />
      </div>
      {loading ? (
        <p className="py-10 text-ink-2">{t("loading")}</p>
      ) : !current ? (
        <div className="max-w-[60ch] space-y-4 py-10">
          <h1 className="text-[40px] md:text-[58px]">{t("allDone")}</h1>
          <p className="text-[17px] text-ink-2">{t("allDoneText")}</p>
          <Link href={back} className="inline-flex min-h-12 items-center border-2 border-ink bg-ink px-5 font-bold text-ground no-underline">
            {t("toMatch")}
          </Link>
        </div>
      ) : (
        <div className="grid gap-5 py-6 md:grid-cols-[minmax(0,1fr)_420px] md:gap-14 md:py-10">
          <figure className="relative m-0 bg-[#1d2125]">
            {current.kind === "field" && main ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`/v1/orgs/${orgId}/videos/${main.id}/panorama`} alt={t("fieldAlt")} className="block w-full outline-[3.5px] outline-attn outline-dashed -outline-offset-8" />
            ) : current.kind === "goal" && media ? (
              <VideoPlayer key={current.c.id} src={`${media}/hls/master.m3u8`} window={{ start_ms: current.c.start_ms, end_ms: current.c.end_ms }} autoPlay />
            ) : null}
            {current.kind === "goal" && (
              <figcaption className="bg-[rgb(10_13_17/0.9)] px-3 py-2 font-mono text-[13px] font-semibold text-[#eef2f5]">
                {t("goalCaption", { clock: clock(current.c.clock_s), video: clock(current.c.goal_ms / 1000) })}
              </figcaption>
            )}
          </figure>
          <div>
            <p className="m-0 text-[13px] font-semibold text-ink-2">{t("questionOf", { n: total - open.length + 1, total })}</p>
            <h1 className="mb-2 text-[40px] leading-[.95] md:text-[58px]">{current.kind === "field" ? t("fieldQuestion") : t("goalQuestion")}</h1>
            <p className="mt-4 max-w-[54ch] text-[17px] text-ink-2">{current.kind === "field" ? t("fieldWhy") : t("goalWhy")}</p>
            <div className="mt-6 grid grid-cols-2 gap-2.5">
              {answers.map((a) => (
                <button
                  key={a.key}
                  type="button"
                  onClick={() => void answer(a)}
                  className={cn(
                    "flex min-h-14 cursor-pointer items-center gap-3.5 border-2 border-ink px-4 text-left text-[17px] font-semibold md:min-h-16",
                    a.first ? "bg-ink text-ground" : "bg-transparent text-ink",
                    answers.length === 2 && "col-span-2",
                  )}
                >
                  {a.numeral && <b className={cn("font-num min-w-9 text-[28px] leading-none md:text-[34px]", a.first ? "text-ground" : "text-club-text")}>{a.numeral}</b>}
                  {a.label}
                </button>
              ))}
              <button type="button" onClick={() => next(current)} className="col-span-2 min-h-[52px] cursor-pointer border-2 border-ink bg-transparent text-[17px] font-bold">
                {t("dontKnow")}
              </button>
            </div>
            <div className="mt-7 flex gap-[3px]" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={total - open.length} aria-label={t("progress", { done: total - open.length, total })}>
              {questions.map((q, i) => (
                <i key={i} className={cn("block h-1.5 flex-1", done.includes(id(q)) ? "bg-ink" : "bg-rule")} />
              ))}
            </div>
            <p className="mt-2 text-[13px] text-ink-2">{t("progress", { done: total - open.length, total })}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function id(q: Question): string {
  return q.kind === "field" ? `field:${q.videoId}` : q.c.id;
}

"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRosterNames } from "@/components/analysis/tagger";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import type { Homography } from "@/lib/spotlight";
import { PersonCrop } from "./person-box";
import { Strip } from "@/components/anlauf/heads";
import { useShell } from "@/components/shell/context";
import { api } from "@/lib/client";
import { matchStyle } from "@/lib/color";
import { useOpponentName } from "@/lib/opponent";
import { cn } from "@/lib/utils";

type Match = Schemas["MatchOut"];
type Candidate = Schemas["GoalCandidateRow"];

type Track = Schemas["TrackOut"];
type Question = { kind: "field"; videoId: string } | { kind: "goal"; c: Candidate } | { kind: "person"; tr: Track; at: number };

// a person question: own tracks without a name, long enough to recognise someone, at most six
const PERSON_MIN_MS = 5000;
const PERSON_MAX = 6;
type Answer = { key: string; label: string; first?: boolean; numeral?: string; run: () => Promise<void> };

const clock = (s: number | null | undefined) => (s == null ? "" : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`);

/**
 * Prüfen (SPEC 7.5): the questions the analysis cannot answer itself, one at a time. The court
 * first (until it is confirmed there are no positions), then the goal candidates, then, once the
 * court is confirmed, the people the analysis follows without a name: a box around the person
 * from the track and the court homography (lib/spotlight.ts personBox). Every answer is saved
 * at once; the screen can be left at any time.
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
    // people only on a confirmed court: without it the box would sit in the wrong place
    if (main && cal?.source === "user_correction" && analysis.data?.chunk_ms) {
      const own = (analysis.data.tracks ?? [])
        .filter((tr) => (tr.team === "home" || tr.team === "home_gk") && !tr.player_id && tr.last_ms - tr.first_ms >= PERSON_MIN_MS)
        .sort((a, b) => b.last_ms - b.first_ms - (a.last_ms - a.first_ms))
        .slice(0, PERSON_MAX)
        .sort((a, b) => a.first_ms - b.first_ms);
      for (const tr of own) q.push({ kind: "person", tr, at: tr.first_ms + Math.min(2000, (tr.last_ms - tr.first_ms) / 2) });
    }
    return q;
  }, [analysis.data, candidates.data, main]);
  const open = questions.filter((q) => !done.includes(id(q)));
  // what was answered in this round, to look at again and change (UX test H12)
  const [answered, setAnswered] = useState<{ q: Question; label: string }[]>([]);
  const [revisit, setRevisit] = useState<number | null>(null);
  const current = revisit != null ? (answered[revisit]?.q ?? null) : (open[0] ?? null);
  const total = questions.length;
  const next = useCallback((q: Question) => setDone((d) => [...d, id(q)]), []);

  const roster = useRosterNames(orgId, match.team_id, match.season_id);
  const players = (roster.data ?? []).filter((r) => r.active);
  const read = current?.kind === "person" && current.tr.number != null ? players.find((r) => r.jersey_number === current.tr.number) : undefined;
  const player = useRef<PlayerHandle>(null);
  const getTime = useCallback(() => player.current?.time() ?? 0, []);
  const getVideo = useCallback(() => player.current?.video() ?? null, []);
  async function identify(tr: Track, playerId: string) {
    await api.PUT("/v1/orgs/{org_id}/videos/{video_id}/tracks/{track_no}/identity", {
      params: { path: { org_id: orgId, video_id: main!.id, track_no: tr.track_no } },
      body: { player_id: playerId, number: null },
    });
    void qc.invalidateQueries({ queryKey: ["analysis", main?.id] });
  }

  const answers: Answer[] = !current
    ? []
    : current.kind === "person"
      ? // the number the analysis read first, then the squad by number: a tap or the shirt number
        [...(read ? [read] : []), ...players.filter((r) => r !== read && r.jersey_number != null).sort((a, b) => a.jersey_number! - b.jersey_number!)]
          .slice(0, 6)
          .map((r, i) => ({ key: `#${r.jersey_number}`, numeral: String(r.jersey_number), first: i === 0 && r === read, label: `${r.first_name} ${r.last_name}`, run: () => identify(current.tr, r.player_id) }))
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
    if (revisit != null) {
      setAnswered((list) => list.map((x, i) => (i === revisit ? { ...x, label: a.label } : x)));
      setRevisit(null);
      return;
    }
    setAnswered((list) => [...list, { q: current, label: a.label }]);
    next(current);
  }
  const skip = (q: Question) => (revisit != null ? setRevisit(null) : next(q));

  // keys 1 to 3 answer, 0 is «Weiss nicht» (desktop); a person: type the shirt number, space is
  // «Weiss nicht»
  const typed = useRef<{ digits: string; timer: number | null }>({ digits: "", timer: null });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!current || e.metaKey || e.ctrlKey || (e.target as HTMLElement)?.closest("input, textarea, select")) return;
      if (current.kind === "person") {
        if (e.key === " ") return (e.preventDefault(), next(current));
        if (!/^\d$/.test(e.key)) return;
        const buf = typed.current;
        buf.digits += e.key;
        if (buf.timer) window.clearTimeout(buf.timer);
        buf.timer = window.setTimeout(() => {
          const r = players.find((x) => x.jersey_number === Number(buf.digits));
          buf.digits = "";
          if (r) void identify(current.tr, r.player_id).then(() => next(current));
        }, 600);
        return;
      }
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
        <span className="min-w-0 truncate text-[15px] font-bold">{t("top", { opponent: `${org.name} ${ta("vsShort")} ${oppName}` })}</span>
        {/* one line on a phone too (UX test B45) */}
        <Link href={back} className="inline-flex min-h-11 shrink-0 items-center border-2 border-ink px-3.5 text-[15px] font-bold whitespace-nowrap text-ink no-underline">
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
          {answered.length > 0 && (
            <section aria-labelledby="answered" data-testid="check-answered">
              <h2 id="answered" className="text-[22px]">{t("answered")}</h2>
              <ul className="m-0 list-none border-t-2 border-ink p-0">
                {answered.map((x, i) => (
                  <li key={id(x.q)} className="flex min-h-12 items-center justify-between gap-3 border-b border-rule text-[17px]">
                    <span>
                      {x.q.kind === "field" ? t("fieldQuestion") : x.q.kind === "person" ? t("personQuestion") : t("goalQuestion")} <b>{x.label}</b>
                    </span>
                    <button type="button" onClick={() => setRevisit(i)} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 font-bold underline underline-offset-4">
                      {t("change")}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <Link href={back} className="inline-flex min-h-12 items-center border-2 border-ink bg-ink px-5 font-bold text-ground no-underline">
            {t("toMatch")}
          </Link>
        </div>
      ) : (
        <div className="grid gap-5 py-6 md:grid-cols-[minmax(0,1fr)_420px] md:gap-14 md:py-10">
          <figure className="relative m-0 self-start bg-[#1d2125]">
            {current.kind === "field" && main ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`/v1/orgs/${orgId}/videos/${main.id}/panorama`} alt={t("fieldAlt")} className="block w-full outline-[3.5px] outline-attn outline-dashed -outline-offset-8" />
            ) : current.kind === "person" && media && analysis.data?.calibration ? (
              <VideoPlayer
                ref={player}
                key={current.tr.track_no}
                src={`${media}/hls/master.m3u8`}
                window={{ start_ms: Math.max(0, current.at - 1500), end_ms: current.at + 2500 }}
                autoPlay
                overlay={
                  <PersonCrop
                    getVideo={getVideo}
                    baseUrl={`/v1/orgs/${orgId}/videos/${main!.id}/tracks`}
                    chunkMs={analysis.data.chunk_ms!}
                    homography={analysis.data.calibration.homography as Homography}
                    imageSize={analysis.data.calibration.image_size as [number, number]}
                    track={current.tr.track_no}
                    getTime={getTime}
                  />
                }
              />
            ) : current.kind === "goal" && media ? (
              <VideoPlayer key={current.c.id} src={`${media}/hls/master.m3u8`} window={{ start_ms: current.c.start_ms, end_ms: current.c.end_ms }} autoPlay />
            ) : null}
            {current.kind === "person" && (
              <figcaption className="bg-[rgb(10_13_17/0.9)] px-3 py-2 font-mono text-[13px] font-semibold text-[#eef2f5]">
                {t("personCaption", { video: clock(current.at / 1000), s: Math.round((current.tr.last_ms - current.tr.first_ms) / 1000), read: current.tr.number ?? "none" })}
              </figcaption>
            )}
            {current.kind === "goal" && (
              <figcaption className="bg-[rgb(10_13_17/0.9)] px-3 py-2 font-mono text-[13px] font-semibold text-[#eef2f5]">
                {t("goalCaption", { clock: clock(current.c.clock_s), video: clock(current.c.goal_ms / 1000) })}
              </figcaption>
            )}
          </figure>
          <div>
            <p className="m-0 flex flex-wrap items-center justify-between gap-3 text-[15px] font-semibold text-ink-2">
              <span>{revisit != null ? t("changing", { answer: answered[revisit]?.label ?? "" }) : t("questionOf", { n: total - open.length + 1, total })}</span>
              {answered.length > 0 && (revisit ?? answered.length) > 0 && (
                <button type="button" onClick={() => setRevisit((revisit ?? answered.length) - 1)} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 font-bold text-ink underline underline-offset-4" data-testid="check-back">
                  {t("back")}
                </button>
              )}
            </p>
            <h1 className="mb-2 text-[40px] leading-[.95] md:text-[58px]">{current.kind === "field" ? t("fieldQuestion") : current.kind === "person" ? t("personQuestion") : t("goalQuestion")}</h1>
            <p className="mt-4 max-w-[54ch] text-[17px] text-ink-2">
              {current.kind === "field" ? t("fieldWhy") : current.kind === "person" ? t("personWhy") : t("goalWhy")}
            </p>

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
              {current.kind === "person" && (
                <label className="col-span-2 block">
                  <span className="mb-1 block text-[15px] font-semibold text-ink-2">{read ? t("personOther") : t("personPick")}</span>
                  <select
                    value=""
                    onChange={(e) => {
                      const id = e.target.value;
                      if (id) void identify(current.tr, id).then(() => next(current));
                    }}
                    className="min-h-14 w-full border-2 border-ink bg-transparent px-3 text-[17px] font-semibold"
                    data-testid="person-pick"
                  >
                    <option value="">{t("personPick")}</option>
                    {players.map((r) => (
                      <option key={r.player_id} value={r.player_id}>
                        {r.jersey_number != null ? `${r.jersey_number} ` : ""}
                        {r.first_name} {r.last_name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {/* aligned like the other answers (UX test B45) */}
              <button type="button" onClick={() => skip(current)} className="col-span-2 min-h-[52px] cursor-pointer border-2 border-ink bg-transparent px-4 text-left text-[17px] font-bold">
                {t("dontKnow")}
              </button>
            </div>
            {current.kind === "person" && <p className="mt-4 text-[15px] text-ink-2 max-md:hidden">{t("personKeys")}</p>}
            <div className="mt-7 flex gap-[3px]" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={total - open.length} aria-label={t("progress", { done: total - open.length, total })}>
              {questions.map((q, i) => (
                <i key={i} className={cn("block h-1.5 flex-1", done.includes(id(q)) ? "bg-ink" : "bg-rule")} />
              ))}
            </div>
            <p className="mt-2 text-[15px] text-ink-2">{t("progress", { done: total - open.length, total })}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function id(q: Question): string {
  return q.kind === "field" ? `field:${q.videoId}` : q.kind === "person" ? `person:${q.tr.track_no}` : q.c.id;
}

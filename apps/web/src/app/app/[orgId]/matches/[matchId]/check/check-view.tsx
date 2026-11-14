"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRosterNames } from "@/components/analysis/tagger";
import { VideoPlayer, type PlayerHandle } from "@/components/video/player";
import type { Homography } from "@/lib/spotlight";
import { CORNERS, cornersOf, FieldCheck } from "./field-check";
import type { Pt } from "@/lib/court-calibration";
import { PersonCrop } from "./person-box";
import { Strip } from "@/components/anlauf/heads";
import { useShell } from "@/components/shell/context";
import { ownName } from "@/lib/own-name";
import { api } from "@/lib/client";
import { matchStyle } from "@/lib/color";
import { useOpponentName } from "@/lib/opponent";
import { formatClock } from "@/lib/format";
import { cn } from "@/lib/utils";
import { buttonClass } from "@/components/ui/button";
import { goalWindow, sameGoal } from "@/lib/goal-window";
import { openMoments, useMatchGraphics } from "@/lib/graphics";
import { useRouter } from "next/navigation";
import { partName, partsOf, partStarts, timelineVideo } from "@/lib/video-parts";
import { ShotSpotPicker } from "@/components/anlauf/shot-spot-picker";
import { useSaveSpot } from "@/components/anlauf/spot-parts";
import { checkMinutes, type SpotAnswer, type SpotZone } from "@/lib/shot-spot";
import type { Pt as HalfPt } from "@/components/anlauf/geometry";

type Match = Schemas["MatchOut"];
type Candidate = Schemas["GoalCandidateRow"];

type Track = Schemas["TrackOut"];
type Question = { kind: "field"; videoId: string; part: number | null; copyFrom: string | null } | { kind: "kickoff"; period: number } | { kind: "goal"; c: Candidate } | { kind: "person"; tr: Track; at: number };

// a person question: own tracks without a name, long enough to recognise someone, at most six
const PERSON_MIN_MS = 5000;
const PERSON_MAX = 6;
type Answer = { key: string; label: string; first?: boolean; numeral?: string; run: () => Promise<void> };
/** «Von wo?» after a confirmed goal (fourth real-video test H7): the goal's event, the place to mark */
type SpotStep = { q: Question; eventId: string; goal: string; suggestion: { zone: SpotZone; kind: "estimated" | "current" } | null; index: number; fromList?: boolean };
type Answered = { q: Question; label: string; eventId?: string; spot?: SpotAnswer };

// one rounding on every screen: full seconds, as the scoreboard (fourth real-video test H8)
const clock = (s: number | null | undefined) => (s == null ? "" : formatClock(s * 1000 + 1));

/**
 * Prüfen (SPEC 7.5): the questions the analysis cannot answer itself, one at a time. The court
 * first (until it is confirmed there are no positions), then the goal candidates, then, once the
 * court is confirmed, the people the analysis follows without a name: a box around the person
 * from the track and the court homography (lib/spotlight.ts personBox). Every answer is saved
 * at once; the screen can be left at any time.
 */
export function CheckView({ orgId, match }: { orgId: string; match: Match }) {
  const t = useTranslations("check");
  const ts = useTranslations("spot");
  const ta = useTranslations("anlauf");
  const tParts = useTranslations("parts");
  const qc = useQueryClient();
  const router = useRouter();
  const { org, teams } = useShell();
  // our side as everywhere else: the team's own name, the club's for «Herren 1» (UX test A06)
  const own = ownName(teams.find((x) => x.id === match.team_id)?.name, org.name);
  const oppName = useOpponentName()(match);
  const main = timelineVideo(match.videos) ?? null;
  const parts = partsOf(match.videos);
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
  // one source for the questions: the server's list, as the mail and the start count them (E07);
  // taken once when the screen opens, so answering does not shuffle the count
  const graphics = useMatchGraphics(orgId, match.id);
  const [asked, setAsked] = useState<{ first: Schemas["CheckOut"][]; more: Schemas["CheckOut"][] } | null>(null);
  useEffect(() => {
    if (!asked && graphics.data) setAsked({ first: graphics.data.checks, more: graphics.data.more_checks ?? [] });
  }, [asked, graphics.data]);
  const [wantMore, setWantMore] = useState(false);
  const [wantPeople, setWantPeople] = useState(false);
  // the server's questions afresh: after a moved court the analysis runs again and writes new
  // candidates (real-video test F3); «Alles geprüft» only once the server has none left
  const [reloading, setReloading] = useState(false);
  const [verified, setVerified] = useState(false);
  // questions left with «Weiss nicht»: not asked again in this round
  const skipped = useRef(new Set<string>());
  const keyOf = (c: Schemas["CheckOut"]) => (c.kind === "field" ? `field:${c.id}` : c.kind === "kickoff" ? `kickoff:${c.frame_ref}` : c.id);
  const fetchChecks = useCallback(async () => {
    const r = await api.GET("/v1/orgs/{org_id}/matches/{match_id}/graphics", { params: { path: { org_id: orgId, match_id: match.id } } });
    return r.data ?? null;
  }, [orgId, match.id]);
  const reload = useCallback(
    async (waitForAnalysis: boolean) => {
      setReloading(true);
      try {
        let g = await fetchChecks();
        // the new analysis: wait until it is done (it rewrites the candidates)
        for (let i = 0; waitForAnalysis && g?.analysis === "running" && i < 600; i++) {
          await new Promise((r) => setTimeout(r, 3000));
          g = await fetchChecks();
        }
        await qc.refetchQueries({ queryKey: ["goal-candidates", match.id] });
        void qc.invalidateQueries({ queryKey: ["graphics", match.id] });
        if (g) {
          const left = (list: Schemas["CheckOut"][]) => list.filter((c) => !skipped.current.has(keyOf(c)));
          setAsked({ first: left(g.checks), more: left(g.more_checks ?? []) });
          setDone([]);
          setVerified(left(g.checks).length === 0);
        } else setVerified(true);
        return g;
      } finally {
        setReloading(false);
      }
    },
    [fetchChecks, qc, match.id],
  );
  const cal0 = analysis.data?.calibration;
  // a person box needs the homography of the very frame: with a panning camera only the hall
  // image's is known, so people are asked only with a fixed camera (E05)
  const people = useMemo<Question[]>(() => {
    if (!main || cal0?.source !== "user_correction" || !analysis.data?.chunk_ms || analysis.data.camera !== "fixed") return [];
    return (analysis.data.tracks ?? [])
      .filter((tr) => (tr.team === "home" || tr.team === "home_gk") && !tr.player_id && tr.last_ms - tr.first_ms >= PERSON_MIN_MS)
      .sort((a, b) => b.last_ms - b.first_ms - (a.last_ms - a.first_ms))
      .slice(0, PERSON_MAX)
      .sort((a, b) => a.first_ms - b.first_ms)
      .map((tr) => ({ kind: "person" as const, tr, at: tr.first_ms + Math.min(2000, (tr.last_ms - tr.first_ms) / 2) }));
  }, [analysis.data, cal0, main]);
  const toQuestions = useCallback(
    (list: Schemas["CheckOut"][]): Question[] =>
      list.flatMap((c): Question[] => {
        // the court of each part of the match (the second half asked only when it was not
        // carried over from the first); the first half's court can be taken over
        if (c.kind === "field")
          return main ? [{ kind: "field", videoId: c.id, part: parts.find((p) => p.id === c.id)?.part ?? null, copyFrom: c.copy_from ?? null }] : [];
        if (c.kind === "kickoff") return [{ kind: "kickoff", period: c.frame_ref }];
        const cand = candidates.data?.candidates.find((x) => x.id === c.id && x.status === "open");
        return cand ? [{ kind: "goal", c: cand }] : [];
      }),
    [candidates.data, main, parts],
  );
  const questions = useMemo<Question[]>(() => {
    if (!asked) return [];
    // the further goal moments with «Weiter prüfen», the people in the picture on their own
    return [...toQuestions(asked.first), ...(wantMore ? toQuestions(asked.more) : []), ...(wantPeople ? people : [])];
  }, [asked, wantMore, wantPeople, toQuestions, people]);
  const moreCount = people.length;
  // goal moments beyond the most important ones: while any is open nothing looks final, «Alles
  // geprüft» only without (third real-video test G1)
  const moreGoals = asked ? toQuestions(asked.more).length : 0;
  const stillOpen = graphics.data ? openMoments(graphics.data) : 0;
  const open = questions.filter((q) => !done.includes(id(q)));
  // what was answered in this round, to look at again and change (UX test H12)
  const [answered, setAnswered] = useState<Answered[]>([]);
  const [revisit, setRevisit] = useState<number | null>(null);
  // the second step of a goal question: where the shot came from, one tap (H7)
  const [spotStep, setSpotStep] = useState<SpotStep | null>(null);
  const saveSpot = useSaveSpot(orgId, match.id);
  const lastReview = useRef<Candidate | null>(null);
  const current = spotStep?.q ?? (revisit != null ? (answered[revisit]?.q ?? null) : (open[0] ?? null));
  const total = questions.length;
  const next = useCallback((q: Question) => setDone((d) => [...d, id(q)]), []);

  // the court on the hall image: the stored court projected back, four handles (UX test B13, B14);
  // a further part of the match has its own hall image and court
  const fieldVideo = current?.kind === "field" ? current.videoId : (main?.id ?? null);
  const partField = useQuery({
    queryKey: ["analysis", fieldVideo],
    enabled: fieldVideo != null && fieldVideo !== main?.id,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/videos/{video_id}/analysis", { params: { path: { org_id: orgId, video_id: fieldVideo! } } })).data ?? null,
  });
  const fieldData = fieldVideo != null && fieldVideo !== main?.id ? partField.data : analysis.data;
  const pano = fieldData?.panorama ?? null;
  const panoSize: [number, number] | null = pano ? [pano.width, pano.height] : null;
  const cal = fieldData?.calibration;
  const inPano = cal && panoSize && cal.image_size[0] === panoSize[0] && cal.image_size[1] === panoSize[1];
  const startCorners = panoSize ? cornersOf(inPano ? (cal.homography as Homography) : null, panoSize) : null;
  const [moved, setMoved] = useState<Pt[] | null>(null);
  const corners = moved ?? startCorners;

  const roster = useRosterNames(orgId, match.team_id, match.season_id);
  const players = (roster.data ?? []).filter((r) => r.active);
  const read = current?.kind === "person" && current.tr.number != null ? players.find((r) => r.jersey_number === current.tr.number) : undefined;
  const player = useRef<PlayerHandle>(null);
  const getTime = useCallback(() => player.current?.time() ?? 0, []);
  const getVideo = useCallback(() => player.current?.video() ?? null, []);
  // an answer counts only once it is saved; a refusal of the API is said, never swallowed (E03)
  const [failed, setFailed] = useState<string | null>(null);
  // «Der Anwurf ist nicht im Video» and, if known, the minute the video's start shows (G8)
  const [absent, setAbsent] = useState(false);
  // minute and second, as the scoreboard shows «8:15» (fourth real-video test H10)
  const [startMinute, setStartMinute] = useState("");
  const [startSecond, setStartSecond] = useState("");
  const must = (r: { error?: unknown; response: Response }) => {
    if (r.error || !r.response.ok) {
      const p = r.error as { detail?: string; title?: string } | undefined;
      throw new Error(p?.detail || p?.title || String(r.response.status));
    }
  };
  async function identify(tr: Track, playerId: string) {
    const r = await api.PUT("/v1/orgs/{org_id}/videos/{video_id}/tracks/{track_no}/identity", {
      params: { path: { org_id: orgId, video_id: main!.id, track_no: tr.track_no } },
      body: { player_id: playerId, number: null },
    });
    must(r);
    void qc.invalidateQueries({ queryKey: ["analysis", main?.id] });
  }

  // a goal already confirmed for the same side inside this question's clip: the same goal again
  // is the likely answer (third real-video test G2)
  const earlier = current?.kind === "goal" && graphics.data ? sameGoal(graphics.data.goals, current.c) : null;
  const answers: Answer[] = !current
    ? []
    : current.kind === "person"
      ? // the number the analysis read first, then the squad by number: a tap or the shirt number
        [...(read ? [read] : []), ...players.filter((r) => r !== read && r.jersey_number != null).sort((a, b) => a.jersey_number! - b.jersey_number!)]
          .slice(0, 6)
          .map((r, i) => ({ key: `#${r.jersey_number}`, numeral: String(r.jersey_number), first: i === 0 && r === read, label: `${r.first_name} ${r.last_name}`, run: () => identify(current.tr, r.player_id) }))
      : current.kind === "kickoff"
      ? [
          {
            key: "1",
            label: t("kickoffNow"),
            first: true,
            run: async () => {
              must(await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/kickoff", { params: { path }, body: { period: current.period, t_ms: Math.round(getTime()) } }));
              for (const key of ["match", "events", "stats", "official-goals", "goal-candidates"]) void qc.invalidateQueries({ queryKey: [key, match.id] });
              router.refresh();
            },
          },
        ]
      : current.kind === "field"
      ? [
          {
            key: "1",
            label: t("fieldYes"),
            first: true,
            run: async () => {
              const vid = { params: { path: { org_id: orgId, video_id: current.videoId } } };
              // moved corners are a court of its own: saved as four points on the hall image;
              // otherwise the recognised court is confirmed as it is
              if (moved && panoSize) {
                must(
                  await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration", {
                    ...vid,
                    body: { space: "panorama", frame_ms: 0, points: moved.map((image, i) => ({ image, court: CORNERS[i]! })) },
                  }),
                );
              } else {
                must(await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/confirm", vid));
              }
              const wasMoved = Boolean(moved && panoSize);
              setMoved(null);
              void qc.invalidateQueries({ queryKey: ["analysis"] });
              void qc.invalidateQueries({ queryKey: ["graphics", match.id] });
              // a moved court runs the analysis again: wait for it, then ask what it found
              if (wasMoved) await reload(true);
            },
          },
          ...(current.copyFrom
            ? [
                {
                  key: "2",
                  label: t("fieldTakeOver"),
                  run: async () => {
                    must(
                      await api.POST("/v1/orgs/{org_id}/videos/{video_id}/calibration/from/{source_id}", {
                        params: { path: { org_id: orgId, video_id: current.videoId, source_id: current.copyFrom! } },
                      }),
                    );
                    setMoved(null);
                    // this part is analysed again with the first half's court: then the rest
                    await reload(true);
                  },
                },
              ]
            : []),
        ]
      : earlier
      ? [
          { key: "1", label: t("sameGoal"), numeral: "1", first: true, run: () => review(current.c, { status: "rejected" }) },
          {
            key: "2",
            label: t("anotherGoal"),
            numeral: "2",
            run: () => review(current.c, { status: "confirmed", side: earlier.team === "own" ? "own" : "opponent", outcome: "goal" }),
          },
        ]
      : [
          {
            key: "1",
            label: t("goalOf", { team: own }),
            numeral: "1",
            // without a suggestion nothing is preselected
            first: current.c.suggested_side === "own",
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
    const r = await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/goal-candidates/{candidate_id}/review", { params: { path: { ...path, candidate_id: c.id } }, body });
    must(r);
    lastReview.current = r.data ?? null;
    void qc.invalidateQueries({ queryKey: ["graphics", match.id] });
  }

  async function answer(a: Answer) {
    if (!current) return;
    lastReview.current = null;
    try {
      setFailed(null);
      await a.run();
    } catch (e) {
      setFailed(e instanceof Error ? e.message : String(e));
      return;
    }
    // a confirmed goal: saved; then «Von wo?» in the same question, the video stays (H7)
    const row = lastReview.current as Candidate | null;
    const goal = current.kind === "goal" && row?.status === "confirmed" && row.outcome === "goal" && row.event_id ? row.event_id : null;
    const index = revisit ?? answered.length;
    const entry: Answered = { q: current, label: a.label, ...(goal ? { eventId: goal } : {}) };
    setAnswered((list) => (revisit != null ? list.map((x, i) => (i === revisit ? entry : x)) : [...list, entry]));
    if (goal && row) {
      const zone = row.shot_zone as SpotZone | null | undefined;
      setSpotStep({ q: current, eventId: goal, goal: a.label, index, suggestion: zone ? { zone, kind: row.zone_source === "coach" ? "current" : "estimated" } : null });
      return;
    }
    if (revisit != null) {
      setRevisit(null);
      return;
    }
    next(current);
  }

  /** The place of the goal: saved at once, then the next question (no «Weiter»). */
  async function pickSpot(step: SpotStep, spot: SpotAnswer, point?: HalfPt) {
    try {
      setFailed(null);
      await saveSpot(step.eventId, spot, point);
    } catch (e) {
      setFailed(e instanceof Error ? e.message : String(e));
      return;
    }
    setAnswered((list) => list.map((x, i) => (i === step.index ? { ...x, spot } : x)));
    setSpotStep(null);
    if (step.fromList) return;
    if (revisit != null) {
      setRevisit(null);
      return;
    }
    next(step.q);
  }
  // keyboard and screen reader: the question «Von wo?» takes the focus when it appears
  useEffect(() => {
    if (spotStep) document.getElementById("spot-question")?.focus({ preventScroll: true });
  }, [spotStep]);
  const replay = () => {
    if (current?.kind !== "goal") return;
    player.current?.seek(goalWindow(current.c).start_ms);
    player.current?.play();
  };
  const skip = (q: Question) => {
    if (spotStep) return void pickSpot(spotStep, "unknown");
    if (revisit != null) return setRevisit(null);
    skipped.current.add(id(q));
    next(q);
  };

  // keys 1 to 3 answer, 0 is «Weiss nicht» (desktop); a person: type the shirt number, space is
  // «Weiss nicht»
  const typed = useRef<{ digits: string; timer: number | null }>({ digits: "", timer: null });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!current || spotStep || e.metaKey || e.ctrlKey || (e.target as HTMLElement)?.closest("input, textarea, select")) return;
      if (current.kind === "person") {
        if (e.key === " ") return (e.preventDefault(), skip(current));
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
      else if (e.key === "0") skip(current);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const media = main ? `/v1/orgs/${orgId}/videos/${main.id}/media` : null;
  // where a half's file starts in the match video: the throw-off of the second half is near there
  const kickoffFrom = (period: number) => {
    const start = period > 1 ? partStarts(match.videos).find((p) => p.part === period)?.start_ms : undefined;
    return start != null ? { start_ms: start, end_ms: Number.MAX_SAFE_INTEGER } : undefined;
  };
  const back = `/app/${orgId}/matches/${match.id}`;
  const loading = candidates.isLoading || graphics.isLoading || !asked || (main != null && analysis.isLoading);
  // the list of this round is done: ask the server whether anything is left before saying so
  const ended = !loading && !current;
  // what is left, said honestly in the strip: the questions and about how long (H7: with «Von wo?»)
  const left = open.length;
  const leftGoals = open.filter((q) => q.kind === "goal").length;
  const leftMinutes = checkMinutes(leftGoals, left - leftGoals);
  useEffect(() => {
    if (ended && !verified && !reloading) void reload(false);
  }, [ended, verified, reloading, reload]);
  return (
    <div style={matchStyle([org.primary_color, org.secondary_color ?? null], match.opponent_colors ? [match.opponent_colors.color, match.opponent_colors.second ?? null] : null) as CSSProperties} data-testid="check">
      <div className="bleed-x -mt-px flex h-[60px] items-center justify-between gap-3 border-b-2 border-ink px-4 md:px-8">
        <span className="min-w-0 truncate text-[15px] font-bold">{t("top", { opponent: `${own} ${ta("vsShort")} ${oppName}` })}</span>
        {/* one line on a phone too (UX test B45) */}
        <Link href={back} className="inline-flex min-h-11 shrink-0 items-center border-2 border-ink px-3.5 text-[15px] font-bold whitespace-nowrap text-ink no-underline">
          {t("later")}
        </Link>
      </div>
      <div className="bleed-x">
        <Strip
          name={own}
          sub={`${ta("vsShort")} ${oppName} · ${left > 0 ? t("openCount", { n: left, minutes: leftMinutes }) : t("count", { n: total > 0 || wantMore ? total : moreGoals })}`}
          own={match.score_own}
          opp={match.score_opponent}
        />
      </div>
      {loading ? (
        <p className="py-10 text-ink-2">{t("loading")}</p>
      ) : reloading || (!current && !verified) ? (
        <p role="status" className="py-10 text-[17px] font-semibold" data-testid="check-reloading">
          {t("reloading")}
        </p>
      ) : !current ? (
        <div className="max-w-[60ch] space-y-4 py-10">
          {!wantMore && moreGoals > 0 ? (
            <div className="space-y-4" data-testid="check-main-done">
              <h1 className="text-[40px] md:text-[58px]">{t("mainDone")}</h1>
              <p className="text-[17px] text-ink-2">{t("mainDoneText", { n: moreGoals, minutes: checkMinutes(moreGoals, 0) })}</p>
              <div className="flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={() => {
                    setVerified(false);
                    setWantMore(true);
                  }}
                  className={buttonClass("primary")}
                  data-testid="check-more"
                >
                  {t("goOn")}
                </button>
                <Link href={back} className="min-h-11 content-center font-bold text-ink underline underline-offset-4">
                  {t("later")}
                </Link>
              </div>
            </div>
          ) : stillOpen > 0 ? (
            // left with «Weiss nicht»: still open, said so, never «Alles geprüft»
            <div className="space-y-4" data-testid="check-left-open">
              <h1 className="text-[40px] md:text-[58px]">{t("roundDone")}</h1>
              <p className="text-[17px] text-ink-2">{t("leftOpen", { n: stillOpen })}</p>
            </div>
          ) : (
            <>
              <h1 className="text-[40px] md:text-[58px]">{t("allDone")}</h1>
              <p className="text-[17px] text-ink-2">{t("allDoneText")}</p>
            </>
          )}
          {/* the people in the picture, offered, not pressed on the coach (E07) */}
          {!wantPeople && moreGoals === 0 && stillOpen === 0 && moreCount > 0 && (
            <button type="button" onClick={() => (setVerified(false), setWantPeople(true))} className={buttonClass("secondary")} data-testid="check-people">
              {t("more", { n: moreCount })}
            </button>
          )}
          {answered.length > 0 && (
            <section aria-labelledby="answered" data-testid="check-answered">
              <h2 id="answered" className="text-[22px]">{t("answered")}</h2>
              <ul className="m-0 list-none border-t-2 border-ink p-0">
                {answered.map((x, i) => (
                  <li key={id(x.q)} className="flex min-h-12 flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-rule py-1.5 text-[17px]" data-testid="check-answered-row">
                    <span className="min-w-0">
                      {/* the match clock per goal moment, the video time small beside it: five «Tor Lakers Stäfa» in a row are told apart (H3, H8) */}
                      {x.q.kind === "goal" && (
                        <span className="mr-2 font-mono text-[15px] font-semibold text-ink-2">{x.q.c.clock_s != null ? `${clock(x.q.c.clock_s)} · ${t("videoAt", { video: clock(x.q.c.goal_ms / 1000) })}` : t("videoAt", { video: clock(x.q.c.goal_ms / 1000) })}</span>
                      )}
                      {x.q.kind === "field" ? t("fieldQuestion") : x.q.kind === "kickoff" ? t("kickoffQuestion", { n: x.q.period }) : x.q.kind === "person" ? t("personQuestion") : t("goalQuestion")} <b>{x.label}</b>
                      {x.eventId && <span className="block text-[15px] text-ink-2">{x.spot && x.spot !== "unknown" ? ts("of", { zone: ts(`zone.${x.spot}` as "zone.la") }) : ts("missing")}</span>}
                    </span>
                    <span className="flex flex-wrap gap-x-4">
                      {x.eventId && (
                        <button
                          type="button"
                          onClick={() => setSpotStep({ q: x.q, eventId: x.eventId!, goal: x.label, index: i, fromList: true, suggestion: x.spot && x.spot !== "unknown" ? { zone: x.spot, kind: "current" } : null })}
                          className="min-h-11 cursor-pointer border-0 bg-transparent p-0 font-bold underline underline-offset-4"
                          data-testid="check-spot-change"
                        >
                          {ts("change")}
                        </button>
                      )}
                      <button type="button" onClick={() => setRevisit(i)} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 font-bold underline underline-offset-4">
                        {t("change")}
                      </button>
                    </span>
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
        // the court gets the whole width: the hall image as large as possible (E04)
        <div className={cn("grid gap-5 py-6 md:gap-14 md:py-10", current.kind === "field" ? "md:grid-cols-1 md:gap-6" : "md:grid-cols-[minmax(0,1fr)_420px]")}>
          <figure className="relative m-0 self-start bg-[#1d2125]">
            {current.kind === "field" && main && panoSize && corners ? (
              <FieldCheck key={current.videoId} src={`/v1/orgs/${orgId}/videos/${current.videoId}/panorama`} alt={t("fieldAlt")} size={panoSize} corners={corners} onChange={setMoved} />
            ) : current.kind === "field" && main ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={`/v1/orgs/${orgId}/videos/${current.videoId}/panorama`} alt={t("fieldAlt")} className="block w-full outline-[3.5px] outline-attn outline-dashed -outline-offset-8" />
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
            ) : current.kind === "kickoff" && media ? (
              // the second half's throw-off: the player starts where the second half's file starts
              <VideoPlayer ref={player} key={`kickoff-${current.period}`} src={`${media}/hls/master.m3u8`} window={kickoffFrom(current.period)} />
            ) : current.kind === "goal" && media ? (
              <VideoPlayer ref={player} key={current.c.id} src={`${media}/hls/master.m3u8`} window={goalWindow(current.c)} autoPlay />
            ) : null}
            {current.kind === "person" && (
              <figcaption className="bg-[rgb(10_13_17/0.9)] px-3 py-2 font-mono text-[13px] font-semibold text-[#eef2f5]">
                {t("personCaption", { video: clock(current.at / 1000), s: Math.round((current.tr.last_ms - current.tr.first_ms) / 1000), read: current.tr.number ?? "none" })}
              </figcaption>
            )}
            {current.kind === "field" && panoSize && (
              <figcaption className="flex flex-wrap items-center justify-between gap-3 bg-[rgb(10_13_17/0.9)] px-3 py-2 text-[15px] font-semibold text-[#eef2f5]">
                <span>{t("fieldDrag")}</span>
                <button type="button" disabled={!moved} onClick={() => setMoved(null)} className="min-h-11 cursor-pointer border-[1.5px] border-[#8d97a1] bg-transparent px-3 font-bold text-white disabled:cursor-default disabled:opacity-50" data-testid="field-reset">
                  {t("fieldReset")}
                </button>
              </figcaption>
            )}
            {current.kind === "goal" && (
              <figcaption className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 bg-[rgb(10_13_17/0.9)] px-3 py-1.5 text-[#eef2f5]">
                <span className="font-mono text-[13px] font-semibold">{current.c.clock_s != null ? t("goalCaption", { clock: clock(current.c.clock_s), video: clock(current.c.goal_ms / 1000) }) : t("videoAt", { video: clock(current.c.goal_ms / 1000) })}</span>
                {/* the coach sees the throw again while answering «Von wo?» (H7) */}
                <button type="button" onClick={replay} className="min-h-11 cursor-pointer border-[1.5px] border-[#8d97a1] bg-transparent px-3 text-[15px] font-bold text-white" data-testid="check-replay">
                  {ts("replay")}
                </button>
              </figcaption>
            )}
          </figure>
          <div>
            <p className="m-0 flex flex-wrap items-center justify-between gap-3 text-[15px] font-semibold text-ink-2">
              <span>{revisit != null ? t("changing", { answer: answered[revisit]?.label ?? "" }) : t("questionOf", { n: total - open.length + 1, total })}</span>
              {/* «Zurück» only where there is a question before this one (fourth real-video test H10) */}
              {!spotStep && answered.length > 0 && (revisit != null ? revisit > 0 : total - open.length > 0) && (
                <button type="button" onClick={() => setRevisit((revisit ?? answered.length) - 1)} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 font-bold text-ink underline underline-offset-4" data-testid="check-back">
                  {t("back")}
                </button>
              )}
            </p>
            {spotStep ? (
              // «Von wo?»: the goal is saved; one tap on the court saves the place and goes on (H7)
              <section aria-labelledby="spot-question" data-testid="spot-step">
                <p role="status" className="m-0 mt-2 text-[17px] font-semibold">
                  <Check aria-hidden className="mr-1.5 inline size-5 align-[-3px] text-win" strokeWidth={3} />
                  {ts("saved", { goal: spotStep.goal })}
                </p>
                <h1 id="spot-question" tabIndex={-1} className="mt-2 mb-2 text-[40px] leading-[.95] outline-none md:text-[58px]">
                  {ts("question")}
                </h1>
                <p className="mt-3 max-w-[54ch] text-[17px] text-ink-2">
                  {ts("why")} {spotStep.suggestion?.kind === "estimated" ? ts("suggestedWhy") : ""}
                </p>
                {failed && (
                  <p role="alert" className="mt-4 max-w-[54ch] border-l-4 border-loss pl-3 text-[17px] font-semibold" data-testid="check-failed">
                    {t("saveFailed")} <span className="block text-[15px] font-normal text-ink-2">{failed}</span>
                  </p>
                )}
                <div className="mt-4">
                  <ShotSpotPicker key={`${spotStep.eventId}-${spotStep.index}`} suggestion={spotStep.suggestion} onPick={(spot, point) => void pickSpot(spotStep, spot, point)} />
                </div>
              </section>
            ) : (
              <>
            <h1 className="mb-2 text-[40px] leading-[.95] md:text-[58px]">{current.kind === "field" ? (current.part && current.part > 1 ? t("fieldQuestionPart", { name: tParts(partName(current.part, parts.length).key, { n: current.part }) }) : t("fieldQuestion")) : current.kind === "kickoff" ? t("kickoffQuestion", { n: current.period }) : current.kind === "person" ? t("personQuestion") : t("goalQuestion")}</h1>
                <p className="mt-4 max-w-[54ch] text-[17px] text-ink-2">
                  {current.kind === "field" ? (current.copyFrom ? t("fieldWhyPart") : t("fieldWhy")) : current.kind === "kickoff" ? t("kickoffWhy") : current.kind === "person" ? t("personWhy") : earlier ? t("sameGoalWhy", { time: clock(earlier.t_ms! / 1000) }) : t("goalWhy")}
                </p>

                {failed && (
                  <p role="alert" className="mt-4 max-w-[54ch] border-l-4 border-loss pl-3 text-[17px] font-semibold" data-testid="check-failed">
                    {t("saveFailed")} <span className="block text-[15px] font-normal text-ink-2">{failed}</span>
                  </p>
                )}
                <div className="mt-6 grid grid-cols-2 gap-2.5">
                  {answers.map((a) => (
                    <button
                      key={a.key}
                      type="button"
                      onClick={() => void answer(a)}
                      className={cn(
                        "flex min-h-14 cursor-pointer items-center gap-3.5 border-2 border-ink px-4 text-left text-[17px] font-semibold md:min-h-16",
                        a.first ? "bg-ink text-ground" : "bg-transparent text-ink",
                        answers.length <= 2 && "col-span-2",
                      )}
                    >
                      {a.numeral && <b className={cn("font-num min-w-9 text-[28px] leading-none md:text-[34px]", a.first ? "text-ground" : "text-club-text")}>{a.numeral}</b>}
                      {a.label}
                    </button>
                  ))}
                  {current.kind === "kickoff" && !absent && (
                    <button type="button" onClick={() => setAbsent(true)} className="col-span-2 min-h-[52px] cursor-pointer border-2 border-ink bg-transparent px-4 text-left text-[17px] font-semibold" data-testid="kickoff-absent">
                      {t("kickoffAbsent")}
                    </button>
                  )}
                  {current.kind === "kickoff" && absent && (
                    <form
                      className="col-span-2 space-y-2 border-2 border-ink p-4"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const minute = startMinute.trim() === "" ? null : Number(startMinute) + (startSecond.trim() === "" ? 0 : Math.min(59, Number(startSecond)) / 60);
                        const period = current.period;
                        void answer({
                          key: "absent",
                          label: t("kickoffAbsent"),
                          run: async () => {
                            const clock_s = minute != null && Number.isFinite(minute) ? (period - 1) * match.period_s + minute * 60 : undefined;
                            must(await api.PUT("/v1/orgs/{org_id}/matches/{match_id}/kickoff", { params: { path }, body: { period, t_ms: 0, absent: true, ...(clock_s != null ? { clock_s } : {}) } }));
                            for (const key of ["match", "events", "stats", "official-goals", "goal-candidates", "graphics"]) void qc.invalidateQueries({ queryKey: [key, match.id] });
                            setAbsent(false);
                            setStartMinute("");
                            setStartSecond("");
                            router.refresh();
                          },
                        });
                      }}
                    >
                      <fieldset className="m-0 border-0 p-0">
                        <legend className="mb-1 block p-0 text-[17px] font-semibold">{t("kickoffStartMinute")}</legend>
                        <span className="mb-2 block text-[15px] text-ink-2">{t("kickoffStartMinuteHint")}</span>
                        <span className="flex items-end gap-2">
                          <label className="block">
                            <span className="mb-1 block text-[15px] font-semibold">{t("kickoffMinute")}</span>
                            <input
                              type="number"
                              min={0}
                              max={Math.round((match.period_s * match.periods) / 60)}
                              inputMode="numeric"
                              value={startMinute}
                              onChange={(e) => setStartMinute(e.target.value)}
                              className="min-h-12 w-24 border-2 border-ink bg-transparent px-3 text-[17px]"
                              data-testid="kickoff-start-minute"
                            />
                          </label>
                          <b aria-hidden className="pb-2.5 text-[22px]">
                            :
                          </b>
                          <label className="block">
                            <span className="mb-1 block text-[15px] font-semibold">{t("kickoffSecond")}</span>
                            <input
                              type="number"
                              min={0}
                              max={59}
                              inputMode="numeric"
                              value={startSecond}
                              onChange={(e) => setStartSecond(e.target.value)}
                              className="min-h-12 w-24 border-2 border-ink bg-transparent px-3 text-[17px]"
                              data-testid="kickoff-start-second"
                            />
                          </label>
                        </span>
                      </fieldset>
                      <button type="submit" className={buttonClass("primary")} data-testid="kickoff-absent-save">
                        {t("kickoffAbsentSave")}
                      </button>
                    </form>
                  )}
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
              </>
            )}
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
  return q.kind === "field" ? `field:${q.videoId}` : q.kind === "kickoff" ? `kickoff:${q.period}` : q.kind === "person" ? `person:${q.tr.track_no}` : q.c.id;
}

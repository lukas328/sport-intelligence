"use client";

import type { Schemas } from "@handball/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useMatchRoster, useMatchSides } from "@/components/domain/match-sides";
import { Button } from "@/components/ui/button";
import { FramesProvider, InlinePersonPlayer, PersonStill } from "@/components/video/person-still";
import { api } from "@/lib/client";
import type { Geometry } from "@/lib/moving-camera";
import type { Analysis } from "./analysis-panel";

type Match = Schemas["MatchOut"];

/** Own-team tracks worth naming, the longest 40; an observed match: the tracks of both teams (L4). */
export function ownTracks(tracks: Analysis["tracks"], both = false) {
  return tracks
    .filter((tr) => tr.team === "home" || tr.team === "home_gk" || (both && (tr.team === "away" || tr.team === "away_gk")))
    .sort((a, b) => b.last_ms - b.first_ms - (a.last_ms - a.first_ms))
    .slice(0, 40);
}

/** The moment a person is shown at: a little after they appear, never past half their time. */
export function personMoment(tr: { first_ms: number; last_ms: number }): number {
  return tr.first_ms + Math.min(2000, (tr.last_ms - tr.first_ms) / 2);
}

/**
 * Manual track identities (M5): own-team tracks to roster players; kept across re-analysis. Each
 * person shows as a still from the video, and plays in a small player right above the list
 * (sticky on a phone), so the coach sees who it is and names them without leaving the step.
 */
export function IdentityPanel({
  orgId,
  match,
  videoId,
  tracks,
  at,
  geometry = null,
  chunkMs = null,
}: {
  orgId: string;
  match: Match;
  videoId: string;
  tracks: Analysis["tracks"];
  at: (videoMs: number) => string;
  /** court -> picture (lib/moving-camera geometryOf), memoised: stills and the ring need it */
  geometry?: Geometry | null;
  chunkMs?: number | null;
}) {
  const t = useTranslations("identity");
  const qc = useQueryClient();
  // an observed match: the other team's people by shirt number, never our roster (L4)
  const roster = useMatchRoster(orgId, match);
  const sides = useMatchSides();
  const neutral = sides?.neutral ?? false;
  const [notice, setNotice] = useState<string | null>(null);
  const [all, setAll] = useState(false);
  const [playing, setPlaying] = useState<Analysis["tracks"][number] | null>(null);
  const video = `/v1/orgs/${orgId}/videos/${videoId}`;
  // in the order they appear, so the coach goes through the video once
  const own = [...ownTracks(tracks, neutral)].sort((a, b) => a.first_ms - b.first_ms);
  // named: a player of the roster, or in an observed match a shirt number somebody set
  const named = (tr: (typeof own)[number]) => Boolean(tr.player_id) || (neutral && tr.identity_source === "user_correction");
  const open = own.filter((tr) => !named(tr));
  // the next open people first; the whole list on request
  // a few seconds on screen is rarely worth a name: those fold away with the rest
  const long = open.filter((tr) => tr.last_ms - tr.first_ms >= 5000);
  const shown = all ? own : [...long.slice(0, 8), ...own.filter(named)].sort((a, b) => a.first_ms - b.first_ms);
  if (own.length === 0) return null;
  const who = (tr: Analysis["tracks"][number]) => (tr.number != null ? t("shirt", { n: tr.number }) : t("track", { n: tr.track_no }));
  async function assign(trackNo: number, playerId: string, number: number | null = null) {
    const { error } = await api.PUT("/v1/orgs/{org_id}/videos/{video_id}/tracks/{track_no}/identity", {
      params: { path: { org_id: orgId, video_id: videoId, track_no: trackNo } },
      body: { player_id: playerId || null, number },
    });
    if (!error) {
      setNotice(t("saved"));
      void qc.invalidateQueries({ queryKey: ["analysis", videoId] });
      void qc.invalidateQueries({ queryKey: ["physical", match.id] });
    }
  }
  const body = (
    <section data-testid="identity-panel" aria-labelledby="identity-title">
        <h2 id="identity-title" className="font-display text-xl">{t("title")}</h2>
        <p className="mt-1 text-sm">
          {open.length > 0 ? t("openCount", { n: open.length, first: at(open[0]!.first_ms) }) : t("allDone")}
        </p>
        <p className="mt-1 text-xs text-muted">{neutral ? t("hintNumber") : t("hint")}</p>
        {playing && (
          // the person plays here, above the list: on a phone it stays in view while scrolling
          <div className="mt-3">
            <InlinePersonPlayer video={video} track={playing} geometry={geometry} chunkMs={chunkMs} title={t("playing", { who: who(playing) })} closeLabel={t("closePlayer")} onClose={() => setPlaying(null)} testId="identity-player" />
          </div>
        )}
        <ul className="mt-3 divide-y divide-border/70 text-sm">
          {shown.map((tr) => (
            <li key={tr.track_no} className="flex flex-wrap items-center gap-2 py-1.5" data-testid="identity-row">
              {geometry && chunkMs != null && (
                <button type="button" className="cursor-pointer border-0 bg-transparent p-0" onClick={() => setPlaying(tr)} aria-label={`${t("playHere")}: ${who(tr)}, ${at(tr.first_ms)}`}>
                  <PersonStill geometry={geometry} tracksUrl={`${video}/tracks`} chunkMs={chunkMs} track={tr.track_no} at={personMoment(tr)} label={who(tr)} className="h-16 w-12" />
                </button>
              )}
              <Button variant="quiet" size="sm" className="min-w-0 justify-start" onClick={() => setPlaying(tr)} aria-pressed={playing?.track_no === tr.track_no} aria-label={`${t("playHere")}: ${who(tr)}, ${at(tr.first_ms)}`}>
                <Play aria-hidden className="size-3 fill-current" />
                <span className="font-score tabular-nums">{at(tr.first_ms)}</span>
                {/* a shirt number the analysis read helps to recognise the person; the track id does not */}
                <span className="text-muted">
                  {who(tr)}
                  {` · ${t("onScreen", { s: Math.round((tr.last_ms - tr.first_ms) / 1000) })}`}
                  {/* an observed match lists both teams: whose person it is */}
                  {neutral && sides && ` · ${tr.team?.startsWith("home") ? sides.own : sides.opp}`}
                </span>
              </Button>
              <label className="sr-only" htmlFor={`track-${tr.track_no}`}>
                {t("track", { n: tr.track_no })}
              </label>
              {neutral ? (
                <input
                  id={`track-${tr.track_no}`}
                  type="number"
                  min={0}
                  max={99}
                  inputMode="numeric"
                  defaultValue={tr.number ?? ""}
                  placeholder={t("numberPlaceholder")}
                  onBlur={(e) => {
                    const v = e.target.value.trim();
                    if (v === String(tr.number ?? "")) return;
                    void assign(tr.track_no, "", v === "" ? null : Number(v));
                  }}
                  className="min-h-11 w-24 bg-raised px-2 text-base ring-1 ring-inset ring-border"
                  data-testid="identity-number"
                />
              ) : (
              <select
                id={`track-${tr.track_no}`}
                value={tr.player_id ?? ""}
                onChange={(e) => void assign(tr.track_no, e.target.value)}
                className="min-h-11 flex-1 bg-raised px-2 text-base ring-1 ring-inset ring-border"
              >
                <option value="">{t("none")}</option>
                {(roster.data ?? [])
                  .filter((r) => r.active)
                  .map((r) => (
                    <option key={r.player_id} value={r.player_id}>
                      {r.jersey_number != null ? `#${r.jersey_number} ` : ""}
                      {r.first_name} {r.last_name}
                    </option>
                  ))}
              </select>
              )}
              {tr.identity_source && <span className="text-xs text-muted">{tr.identity_source === "model" ? t("auto") : t("manual")}</span>}
            </li>
          ))}
        </ul>
        {own.length > shown.length && (
          <Button variant="ghost" size="sm" className="mt-1" onClick={() => setAll(true)}>
            {t("showAll", { n: own.length })}
          </Button>
        )}
        {notice && (
          <p className="mt-2 text-xs text-ok" aria-live="polite">
            {notice}
          </p>
        )}
    </section>
  );
  // one hidden video for every still of the list
  return geometry ? <FramesProvider src={`${video}/media/hls/master.m3u8`}>{body}</FramesProvider> : body;
}

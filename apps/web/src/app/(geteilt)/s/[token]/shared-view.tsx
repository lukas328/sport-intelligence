"use client";

import type { PlayDoc } from "@handball/tactics";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { PlayEditor } from "@/components/tactics/play-editor";
import { SectionHead } from "@/components/anlauf/blocks";
import { EmptyField } from "@/components/anlauf/bundle";
import { ClubMark } from "@/components/shell/club-mark";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { VideoPlayer } from "@/components/video/player";
import { cn } from "@/lib/utils";
import type { Schemas } from "@handball/api-client";
import { CameraFrame, TacticsCamera } from "@/components/anlauf/tactics-camera";
import { VIEWS } from "@/components/anlauf/geometry";
import { cameraScene } from "@/lib/graphics";
import { MINI } from "@/lib/mini-field";

export interface Shared {
  kind: "play" | "match" | "playlist" | "highlight" | "scene" | "collection";
  title: string;
  team: string;
  expires_at: string;
  shared_by?: string | null;
  play?: { name: string; category: string; formation: string | null; description: string | null; doc: PlayDoc };
  match?: {
    kickoff_at: string;
    is_home: boolean;
    opponent: string;
    score_own: number | null;
    score_opponent: number | null;
    own: Record<string, number | null>;
    opponent_stats: Record<string, number | null>;
    players: { number: number | null; goals: number; shots: number; saves: number; turnovers: number }[];
    video_id: string | null;
  };
  highlight?: { format: string; scenes: number };
  playlist?: { title: string; description: string | null; clips: { id: string; title: string | null; start_ms: number; end_ms: number; video_id: string | null }[] };
  scene?: SharedRun;
  collection?: SharedRun;
}

/** A shared scene (a run of one) or collection: scenes, plays and notes in order. */
interface SharedRun {
  title: string;
  items: {
    kind: "scene" | "play" | "note";
    text: string | null;
    play: { id: string; name: string } | null;
    scene: { id: string; title: string | null; start_ms: number; end_ms: number; video_id: string | null; camera?: Schemas["SceneCameraOut"] | null } | null;
  }[];
}

const pct = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v * 100)} %`);

export function SharedView({ token, data, club = null, clubColour = null }: { token: string; data: Shared; club?: string | null; clubColour?: string | null }) {
  const t = useTranslations("share");
  const ts = useTranslations("stats");
  const format = useFormatter();
  const media = (videoId: string) => `/v1/share/${token}/videos/${videoId}/media`;
  const owner = [club, data.team].filter((x, i, a) => x && a.indexOf(x) === i).join(" ");
  const run = data.scene ?? data.collection;
  const scenes = run?.items.filter((i) => i.scene) ?? [];
  const seconds = Math.round(scenes.reduce((n, i) => n + (i.scene!.end_ms - i.scene!.start_ms), 0) / 1000);
  const eyebrow = run
    ? t("runKick", { kind: data.collection ? "collection" : "scene", n: scenes.length, length: duration(seconds) })
    : `${owner} · ${t("readOnly", { date: format.dateTime(new Date(data.expires_at), { dateStyle: "medium" }) })}`;
  const days = Math.max(0, Math.ceil((Date.parse(data.expires_at) - Date.now()) / 86_400_000));
  return (
    <div data-testid="shared">
      {/* the club's own narrow head: who shared it, nothing of the app around it */}
      <div className="bleed-x flex h-[60px] items-center justify-between gap-3 border-b-2 border-ink px-4 md:px-8">
        <span className="font-slant flex min-w-0 items-center gap-2.5 text-[17px] md:text-xl">
          <ClubMark org={{ id: "", name: club ?? data.team, has_logo: false, primary_color: clubColour ?? "" }} className="h-[30px] w-[27px] text-[14px]" />
          <span className="truncate">{owner}</span>
        </span>
        <span className="shrink-0 text-[15px] text-ink-2">{data.shared_by ? t("sharedBy", { name: data.shared_by }) : t("viewOnly")}</span>
      </div>
      <PageHeader eyebrow={eyebrow} title={data.title} className="mt-6 md:mt-8" />
      {data.play && (
        <>
          {data.play.description && <p className="whitespace-pre-line text-sm">{data.play.description}</p>}
          <PlayEditor orgId="" teamId="" editable={false} initialDoc={data.play.doc} play={null} />
        </>
      )}
      {data.match && <MatchShare m={data.match} media={media} t={t} ts={ts} format={format} />}
      {data.playlist && <PlaylistShare p={data.playlist} media={media} />}
      {run && <RunShare run={run} media={media} days={days} />}
      {data.highlight && (
        <video
          controls
          preload="metadata"
          src={`/v1/share/${token}/reel.mp4`}
          aria-label={data.title}
          className={data.highlight.format === "9x16" ? "mx-auto max-h-[80vh]" : "w-full"}
        />
      )}
    </div>
  );
}

function MatchShare({ m, media, ts, format }: { m: NonNullable<Shared["match"]>; media: (v: string) => string; t: (k: string) => string; ts: (k: string) => string; format: ReturnType<typeof useFormatter> }) {
  const rows: [string, string | number, string | number][] = [
    [ts("goals"), m.own.goals ?? 0, m.opponent_stats.goals ?? 0],
    [ts("shots"), m.own.shots ?? 0, m.opponent_stats.shots ?? 0],
    [ts("shootingPct"), pct(m.own.shooting_pct), pct(m.opponent_stats.shooting_pct)],
    [ts("saves"), m.own.saves ?? 0, m.opponent_stats.saves ?? 0],
    [ts("turnovers"), m.own.turnovers ?? 0, m.opponent_stats.turnovers ?? 0],
    [ts("suspensions"), m.own.suspensions ?? 0, m.opponent_stats.suspensions ?? 0],
  ];
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">{format.dateTime(new Date(m.kickoff_at), { dateStyle: "full" })}</p>
      {m.score_own != null && m.score_opponent != null && (
        <p className="text-3xl font-bold tabular-nums">
          {m.score_own}:{m.score_opponent} <span className="text-base font-normal text-muted">{m.opponent}</span>
        </p>
      )}
      {m.video_id && <VideoPlayer src={`${media(m.video_id)}/hls/master.m3u8`} />}
      <Card>
        <table className="w-full text-sm">
          <caption className="sr-only">{ts("comparison")}</caption>
          <tbody>
            {rows.map(([label, a, b]) => (
              <tr key={label} className="border-t border-border/70 first:border-0">
                <th scope="row" className="py-1.5 text-left font-normal">{label}</th>
                <td className="text-right tabular-nums">{a}</td>
                <td className="text-right tabular-nums">{b}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {m.players.length > 0 && (
        <Card>
          <table className="w-full text-sm">
            <caption className="text-left font-semibold">{ts("player")}</caption>
            <tbody>
              {m.players.map((p, i) => (
                <tr key={i} className="border-t border-border/70">
                  <th scope="row" className="py-1 text-left font-normal">#{p.number ?? "?"}</th>
                  <td className="text-right tabular-nums">
                    {p.goals}/{p.shots}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

function PlaylistShare({ p, media }: { p: NonNullable<Shared["playlist"]>; media: (v: string) => string }) {
  const t = useTranslations("share");
  const clips = p.clips.filter((c) => c.video_id);
  const [i, setI] = useState(0);
  const clip = clips[i];
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div>
        {clip && (
          <VideoPlayer
            key={clip.video_id}
            src={`${media(clip.video_id!)}/hls/master.m3u8`}
            window={{ start_ms: clip.start_ms, end_ms: clip.end_ms }}
            onWindowEnd={() => setI((x) => Math.min(x + 1, clips.length - 1))}
            autoPlay={i > 0}
          />
        )}
      </div>
      <ol className="space-y-1 text-sm">
        {clips.map((c, k) => (
          <li key={c.id}>
            <button onClick={() => setI(k)} aria-current={k === i ? "true" : undefined} className={cn("w-full px-2 py-1.5 text-left", k === i ? "bg-accent text-accent-contrast" : "hover:bg-surface")}>
              {k + 1}. {c.title ?? t("scene")}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}

/**
 * Scenes play one after the other (SPEC 7.8): the video with the note of the running scene,
 * «Nächste Szene», and the Ablauf at the side: number, Minifeld, title, length, seen or running.
 */
function RunShare({ run, media, days }: { run: SharedRun; media: (v: string) => string; days: number }) {
  const t = useTranslations("share");
  const ta = useTranslations("anlauf");
  const scenes = run.items.filter((i) => i.scene?.video_id);
  const intro = run.items.find((i) => i.kind === "note" && i.text)?.text ?? null;
  const [k, setK] = useState(0);
  const [mode, setMode] = useState<"video" | "taktik">("video");
  const cur = scenes[k];
  const next = () => setK((x) => Math.min(x + 1, scenes.length - 1));
  // the positions before a goal, where the court was confirmed (UX test B15)
  const camOf = (i: (typeof scenes)[number] | undefined) => (i?.scene?.camera ? cameraScene(i.scene.camera, i.scene.title) : null);
  const cam = camOf(cur);
  const shown = cam ? mode : "video";
  const toggle = cam && (
    <div role="group" aria-label={t("viewMode")} className="flex">
      {(["video", "taktik"] as const).map((v) => (
        <button
          key={v}
          type="button"
          aria-pressed={shown === v}
          onClick={() => setMode(v)}
          className={cn("min-h-11 cursor-pointer border-2 border-ink px-4 text-[15px] font-bold first:border-r-0", shown === v ? "bg-ink text-ground" : "bg-transparent text-ink")}
        >
          {ta(v === "video" ? "modeVideo" : "modeTaktik")}
        </button>
      ))}
    </div>
  );
  return (
    <div className="grid gap-x-10 gap-y-8 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="min-w-0">
        {toggle && <div className="mb-3">{toggle}</div>}
        {cur && shown === "video" && (
          <VideoPlayer key={`${cur.scene!.id}-${k}`} src={`${media(cur.scene!.video_id!)}/hls/master.m3u8`} window={{ start_ms: cur.scene!.start_ms, end_ms: cur.scene!.end_ms }} onWindowEnd={next} autoPlay={k > 0} />
        )}
        {cam && shown === "taktik" && (
          <div data-testid="shared-tactics">
            <TacticsCamera
              key={`cam-${k}`}
              scene={cam}
              view="halfB"
              width={900}
              dot={17}
              text={{ label: ta("cameraLabel", { label: cur?.scene?.title ?? t("scene") }), pause: ta("pause"), play: ta("play"), notFound: ta("ballNotFound"), noBall: ta("noBall"), caption: null }}
            />
          </div>
        )}
        {cur?.text && <p className="mt-4 border-l-4 border-club-text pl-3 text-[17px] italic">{cur.text}</p>}
        <div className="mt-5 flex flex-wrap gap-3">
          <button type="button" onClick={next} disabled={k >= scenes.length - 1} className="min-h-12 cursor-pointer border-2 border-ink bg-ink px-5 font-bold text-ground disabled:cursor-default disabled:opacity-50">
            {t("nextScene")}
          </button>
          <a href="#ablauf" className="inline-flex min-h-12 items-center border-2 border-ink px-5 font-bold text-ink no-underline">
            {t("allScenes", { n: scenes.length })}
          </a>
        </div>
      </div>
      <aside id="ablauf" className="min-w-0">
        <SectionHead title={t("run")} />
        {intro && <p className="-mt-1 mb-3 text-[15px] text-ink-2">{intro}</p>}
        <ol className="m-0 list-none p-0">
          {scenes.map((i, n) => {
            const on = n === k;
            const len = Math.round((i.scene!.end_ms - i.scene!.start_ms) / 1000);
            return (
              <li key={`${i.scene!.id}-${n}`}>
                <button
                  type="button"
                  onClick={() => setK(n)}
                  aria-current={on ? "true" : undefined}
                  className={cn("grid w-full cursor-pointer grid-cols-[28px_56px_minmax(0,1fr)_auto] items-center gap-2.5 border-b border-rule px-2 py-2.5 text-left", on ? "bg-attn text-attn-ink" : "bg-transparent text-ink hover:bg-ink/5")}
                >
                  <b className="font-num text-xl">{n + 1}</b>
                  {(() => {
                    const c = camOf(i);
                    // the Minifeld: the last frame of the positions, or the empty field
                    return c ? (
                      <svg aria-hidden viewBox={VIEWS.halfB.box.join(" ")} className="block w-14 bg-court" data-testid="shared-mini">
                        <CameraFrame scene={c} view={MINI.view} width={MINI.width} dot={MINI.dot} t={1} />
                      </svg>
                    ) : (
                      <EmptyField />
                    );
                  })()}
                  <span className="min-w-0 text-[15px] leading-snug font-semibold">
                    {i.scene!.title ?? t("scene")}
                    <small className={cn("block text-[15px] font-normal", on ? "text-attn-ink" : "text-ink-2")}>{on ? t("running") : n < k ? t("seen") : ""}</small>
                  </span>
                  <span className="font-mono text-[13px]">{duration(len)}</span>
                </button>
              </li>
            );
          })}
        </ol>
        <p className="mt-4 text-[15px] text-ink-2">{t("onlyLink", { days })}</p>
      </aside>
    </div>
  );
}

function duration(s: number): string {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

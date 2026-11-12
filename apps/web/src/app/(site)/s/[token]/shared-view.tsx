"use client";

import type { PlayDoc } from "@handball/tactics";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { PlayEditor } from "@/components/tactics/play-editor";
import { Card } from "@/components/ui/card";
import { VideoPlayer } from "@/components/video/player";
import { cn } from "@/lib/utils";

export interface Shared {
  kind: "play" | "match" | "playlist" | "highlight" | "scene" | "collection";
  title: string;
  team: string;
  expires_at: string;
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
    scene: { id: string; title: string | null; start_ms: number; end_ms: number; video_id: string | null } | null;
  }[];
}

const pct = (v: number | null | undefined) => (v == null ? "-" : `${Math.round(v * 100)} %`);

export function SharedView({ token, data }: { token: string; data: Shared }) {
  const t = useTranslations("share");
  const ts = useTranslations("stats");
  const format = useFormatter();
  const media = (videoId: string) => `/v1/share/${token}/videos/${videoId}/media`;
  return (
    <div className="space-y-4" data-testid="shared">
      <header>
        <p className="text-sm text-muted">
          {data.team} · {t("readOnly", { date: format.dateTime(new Date(data.expires_at), { dateStyle: "medium" }) })}
        </p>
        <h1 className="text-2xl font-bold sm:text-[1.75rem]">{data.title}</h1>
      </header>
      {data.play && (
        <>
          {data.play.description && <p className="whitespace-pre-line text-sm">{data.play.description}</p>}
          <PlayEditor orgId="" teamId="" editable={false} initialDoc={data.play.doc} play={null} />
        </>
      )}
      {data.match && <MatchShare m={data.match} media={media} t={t} ts={ts} format={format} />}
      {data.playlist && <PlaylistShare p={data.playlist} media={media} />}
      {(data.scene ?? data.collection) && <RunShare run={(data.scene ?? data.collection)!} media={media} />}
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

/** Scenes play one after the other with the coach's note; notes and plays are listed in order. */
function RunShare({ run, media }: { run: SharedRun; media: (v: string) => string }) {
  const notes = run.items.filter((i) => i.kind !== "scene" && i.text);
  const scenes = run.items.filter((i) => i.scene);
  return (
    <div className="space-y-4">
      <PlaylistShare
        p={{
          title: run.title,
          description: null,
          clips: scenes.map((i) => ({ ...i.scene!, title: [i.scene!.title, i.text].filter(Boolean).join(": ") || null })),
        }}
        media={media}
      />
      {notes.length > 0 && (
        <ul className="space-y-2 text-sm">
          {notes.map((i, k) => (
            <li key={k} className="whitespace-pre-line">
              {i.play ? `${i.play.name}: ` : ""}
              {i.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

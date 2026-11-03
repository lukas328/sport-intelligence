"use client";

import type { Schemas } from "@handball/api-client";
import { LIMITS, TACTICS_FORMAT_VERSION, nextFrame, stateAt, totalDuration, validate, type Frame, type PlayDoc, type Side } from "@handball/tactics";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { cn } from "@/lib/utils";
import { Board, type Tool } from "./board";

type Play = Schemas["PlayOut"];
const CATEGORIES = ["attack", "defence", "fast_break", "set_piece", "seven_m", "other"] as const;
const TOOLS: Tool[] = ["move", "run", "pass", "dribble", "screen", "ball"];
const SPEEDS = [0.5, 1, 2] as const;

export const EMPTY_DOC: PlayDoc = {
  formatVersion: TACTICS_FORMAT_VERSION,
  court: "half",
  frames: [{ tokens: [], ball: null, arrows: [], note: "", duration_ms: 2000 }],
};

export function PlayEditor({
  orgId,
  teamId,
  play,
  initialDoc,
  initialMeta,
  source,
  editable,
}: {
  orgId: string;
  teamId: string;
  play?: Play | null;
  initialDoc?: PlayDoc;
  initialMeta?: { name?: string; category?: string; formation?: string | null; tags?: string[] };
  source?: { match_id: string; t_ms: number } | null;
  editable: boolean;
}) {
  const t = useTranslations("tactics");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const router = useRouter();
  const [doc, setDoc] = useState<PlayDoc>((play?.doc as unknown as PlayDoc | undefined) ?? initialDoc ?? EMPTY_DOC);
  const [idx, setIdx] = useState(0);
  const [tool, setTool] = useState<Tool>("move");
  const [selected, setSelected] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [clock, setClock] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<ErrorKey | "invalid" | null>(null);
  const frame = doc.frames[Math.min(idx, doc.frames.length - 1)]!;

  // playback with requestAnimationFrame; stops at the end
  const raf = useRef(0);
  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    const total = totalDuration(doc);
    const tick = (now: number) => {
      setClock((c) => {
        const next = c + (now - last) * speed;
        last = now;
        if (next >= total) {
          setPlaying(false);
          return total;
        }
        return next;
      });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [playing, speed, doc]);
  const live = playing || clock > 0 ? stateAt(doc, clock) : null;

  function setFrame(f: Frame) {
    setDoc((d) => ({ ...d, frames: d.frames.map((x, i) => (i === idx ? f : x)) }));
    setDirty(true);
  }
  function setFrames(frames: Frame[], to: number) {
    setDoc((d) => ({ ...d, frames }));
    setIdx(Math.max(0, Math.min(to, frames.length - 1)));
    setDirty(true);
  }
  function addToken(side: Side) {
    if (frame.tokens.length >= LIMITS.tokens) return;
    const n = frame.tokens.filter((k) => k.side === side).length + 1;
    let id = `${side[0]}${n}`;
    while (frame.tokens.some((k) => k.id === id)) id += "x";
    const x = doc.court === "half" ? (side === "own" ? 28 : 33) : side === "own" ? 15 : 25;
    setFrame({ ...frame, tokens: [...frame.tokens, { id, side, label: String(n), x, y: 2 + ((n * 3) % 17) }] });
    setSelected(id);
  }
  const sel = frame.tokens.find((k) => k.id === selected) ?? null;

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const problems = validate(doc);
    if (problems.length) {
      setFailure("invalid");
      return;
    }
    const f = new FormData(e.currentTarget);
    const meta = {
      name: String(f.get("name") ?? "").trim(),
      category: String(f.get("category")) as (typeof CATEGORIES)[number],
      formation: String(f.get("formation") ?? "").trim() || null,
      description: String(f.get("description") ?? "").trim() || null,
      tags: String(f.get("tags") ?? "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      shared_with_players: f.get("shared") === "on",
    };
    const body = { ...meta, doc: doc as unknown as Schemas["PlayDocIn"] };
    const res = play
      ? await api.PATCH("/v1/orgs/{org_id}/plays/{play_id}", { params: { path: { org_id: orgId, play_id: play.id } }, body })
      : await api.POST("/v1/orgs/{org_id}/teams/{team_id}/plays", {
          params: { path: { org_id: orgId, team_id: teamId } },
          body: { ...body, source: source ?? null },
        });
    if (res.error || !res.data) return setFailure(errorKey(res.error));
    setFailure(null);
    setDirty(false);
    setNotice(t("saved"));
    if (!play) router.replace(`/app/${orgId}/plays/${res.data.id}`);
    else router.refresh();
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="space-y-3">
        {editable && (
          <div className="flex flex-wrap items-center gap-1" role="toolbar" aria-label={t("tools")}>
            {TOOLS.map((k) => (
              <button
                key={k}
                aria-pressed={tool === k}
                onClick={() => setTool(k)}
                className={cn("rounded border px-2 py-1 text-sm", tool === k ? "border-accent bg-accent text-accent-contrast" : "border-border")}
              >
                {t(`tool_${k}`)}
              </button>
            ))}
            <span className="mx-1 h-6 w-px bg-border" aria-hidden />
            <Button variant="secondary" className="min-h-8 px-2 text-sm" onClick={() => addToken("own")}>
              + {t("own")}
            </Button>
            <Button variant="secondary" className="min-h-8 px-2 text-sm" onClick={() => addToken("opp")}>
              + {t("opp")}
            </Button>
            <Button
              variant="ghost"
              className="min-h-8 px-2 text-sm"
              disabled={frame.arrows.length === 0}
              onClick={() => setFrame({ ...frame, arrows: frame.arrows.slice(0, -1) })}
            >
              {t("undoArrow")}
            </Button>
            <Button variant="ghost" className="min-h-8 px-2 text-sm" disabled={!frame.ball} onClick={() => setFrame({ ...frame, ball: null })}>
              {t("removeBall")}
            </Button>
            <label className="ml-auto flex items-center gap-1 text-sm">
              {t("court")}
              <select
                value={doc.court}
                onChange={(e) => (setDoc({ ...doc, court: e.target.value as "half" | "full" }), setDirty(true))}
                className="min-h-8 rounded border border-border bg-background px-1"
              >
                <option value="half">{t("court_half")}</option>
                <option value="full">{t("court_full")}</option>
              </select>
            </label>
          </div>
        )}
        <Board
          frame={frame}
          live={live}
          court={doc.court}
          editable={editable && !live}
          tool={tool}
          selected={selected}
          onSelect={setSelected}
          onChange={setFrame}
          label={t("board")}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              if (!playing && clock >= totalDuration(doc)) setClock(0);
              setPlaying((p) => !p);
            }}
            disabled={doc.frames.length < 2}
          >
            {playing ? t("pause") : t("play")}
          </Button>
          {(playing || clock > 0) && (
            <Button variant="ghost" onClick={() => (setPlaying(false), setClock(0))}>
              {t("stop")}
            </Button>
          )}
          <div role="group" aria-label={t("speed")} className="flex gap-1">
            {SPEEDS.map((s) => (
              <button key={s} aria-pressed={speed === s} onClick={() => setSpeed(s)} className={cn("rounded px-2 py-1 text-xs", speed === s ? "bg-accent text-accent-contrast" : "bg-surface")}>
                {s}×
              </button>
            ))}
          </div>
          <ol className="flex flex-wrap gap-1" aria-label={t("frames")}>
            {doc.frames.map((_, i) => (
              <li key={i}>
                <button
                  aria-current={i === idx ? "step" : undefined}
                  onClick={() => (setPlaying(false), setClock(0), setIdx(i))}
                  className={cn("size-8 rounded border text-sm tabular-nums", i === idx ? "border-accent bg-accent text-accent-contrast" : "border-border")}
                >
                  {i + 1}
                </button>
              </li>
            ))}
          </ol>
          {editable && (
            <>
              <Button
                variant="secondary"
                className="min-h-8 px-2 text-sm"
                disabled={doc.frames.length >= LIMITS.frames}
                onClick={() => setFrames([...doc.frames.slice(0, idx + 1), nextFrame(frame), ...doc.frames.slice(idx + 1)], idx + 1)}
              >
                + {t("frame")}
              </Button>
              <Button
                variant="ghost"
                className="min-h-8 px-2 text-sm"
                disabled={doc.frames.length <= 1}
                onClick={() => setFrames(doc.frames.filter((_, i) => i !== idx), idx - 1)}
              >
                {t("deleteFrame")}
              </Button>
            </>
          )}
        </div>
        {frame.note && !editable && <p className="rounded bg-surface p-2 text-sm">{frame.note}</p>}
        {editable && (
          <div className="grid gap-2 sm:grid-cols-[1fr_10rem]">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t("note")}</span>
              <textarea
                value={frame.note}
                maxLength={LIMITS.note}
                rows={2}
                onChange={(e) => setFrame({ ...frame, note: e.target.value })}
                className="rounded-md border border-border bg-background px-2 py-1"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t("duration")}</span>
              <select
                value={frame.duration_ms}
                onChange={(e) => setFrame({ ...frame, duration_ms: Number(e.target.value) })}
                className="min-h-10 rounded-md border border-border bg-background px-2"
              >
                {[1000, 1500, 2000, 3000, 4000, 6000].map((ms) => (
                  <option key={ms} value={ms}>
                    {ms / 1000} s
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
        {editable && sel && (
          <div className="flex flex-wrap items-end gap-2 rounded bg-surface p-2 text-sm" aria-live="polite">
            <label className="flex flex-col gap-1">
              <span className="font-medium">{t("label")}</span>
              <input
                value={sel.label}
                maxLength={3}
                onChange={(e) => setFrame({ ...frame, tokens: frame.tokens.map((k) => (k.id === sel.id ? { ...k, label: e.target.value } : k)) })}
                className="min-h-9 w-20 rounded-md border border-border bg-background px-2"
              />
            </label>
            <Button
              variant="ghost"
              className="min-h-9 px-2"
              onClick={() => (setFrame({ ...frame, tokens: frame.tokens.filter((k) => k.id !== sel.id) }), setSelected(null))}
            >
              {t("removeToken")}
            </Button>
            <p className="text-xs text-muted">{t("keyboardHint")}</p>
          </div>
        )}
      </div>

      <Card className="h-fit space-y-3">
        {editable ? (
          <form onSubmit={save} className="space-y-3" aria-label={t("details")}>
            <Input label={t("name")} name="name" required maxLength={120} defaultValue={play?.name ?? initialMeta?.name ?? ""} />
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t("category")}</span>
              <select name="category" defaultValue={play?.category ?? initialMeta?.category ?? "attack"} className="min-h-10 rounded-md border border-border bg-background px-2">
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {t(`cat_${c}`)}
                  </option>
                ))}
              </select>
            </label>
            <Input label={t("formation")} name="formation" maxLength={20} defaultValue={play?.formation ?? initialMeta?.formation ?? ""} />
            <Input label={t("tags")} name="tags" maxLength={300} defaultValue={(play?.tags ?? initialMeta?.tags ?? []).join(", ")} />
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t("description")}</span>
              <textarea name="description" rows={3} maxLength={4000} defaultValue={play?.description ?? ""} className="rounded-md border border-border bg-background px-2 py-1" />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" name="shared" defaultChecked={play?.shared_with_players ?? false} />
              {t("shared")}
            </label>
            <Button type="submit" className="w-full">
              {t("save")}
            </Button>
            {dirty && <p className="text-xs text-muted">{t("unsaved")}</p>}
            {play && (
              <Button
                variant="danger"
                className="w-full"
                onClick={async () => {
                  if (!window.confirm(t("deleteConfirm"))) return;
                  await api.DELETE("/v1/orgs/{org_id}/plays/{play_id}", { params: { path: { org_id: orgId, play_id: play.id } } });
                  router.push(`/app/${orgId}/teams/${teamId}/plays`);
                  router.refresh();
                }}
              >
                {tc("delete")}
              </Button>
            )}
          </form>
        ) : (
          <div className="space-y-2 text-sm">
            <h2 className="text-lg font-semibold">{play?.name}</h2>
            <p className="text-muted">
              {t(`cat_${(play?.category ?? "other") as "other"}`)}
              {play?.formation && ` · ${play.formation}`}
            </p>
            {play?.description && <p className="whitespace-pre-line">{play.description}</p>}
          </div>
        )}
        {source && (
          <a className="block text-sm text-accent underline" href={`/app/${orgId}/matches/${source.match_id}?t=${source.t_ms}`}>
            {t("openSource")}
          </a>
        )}
        <div aria-live="polite">
          {failure && <Alert className="py-2">{failure === "invalid" ? t("invalid") : te(failure)}</Alert>}
          {notice && !failure && (
            <Alert kind="success" className="py-2">
              {notice}
            </Alert>
          )}
        </div>
      </Card>
    </div>
  );
}

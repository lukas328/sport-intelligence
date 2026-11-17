"use client";

import type { Schemas } from "@handball/api-client";
import {
  LIMITS,
  TACTICS_FORMAT_VERSION,
  freeSpot,
  mirrorDoc,
  nextFrame,
  stateAt,
  totalDuration,
  validate,
  type Frame,
  type PlayDoc,
  type Side,
} from "@handball/tactics";
import { Eye, FlipHorizontal2, Maximize2, Minimize2, Pause, Pencil, Play, Plus, Redo2, RotateCcw, Trash2, Undo2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { useConfirm } from "@/components/ui/confirm";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { cn } from "@/lib/utils";
import { Board, type Tool } from "./board";
import { TokenDot, ToolIcon } from "./tool-icon";

type Play = Schemas["PlayOut"];
const CATEGORIES = ["attack", "defence", "fast_break", "set_piece", "seven_m", "other"] as const;
const TOOLS: Tool[] = ["move", "run", "pass", "dribble", "screen", "ball"];
const SPEEDS = [0.5, 1, 2] as const;
const HISTORY = 100;

export const EMPTY_DOC: PlayDoc = {
  formatVersion: TACTICS_FORMAT_VERSION,
  court: "half",
  frames: [{ tokens: [], ball: null, arrows: [], note: "", duration_ms: 2000 }],
};

type Snap = { doc: PlayDoc; idx: number };

/** Undo and redo over the whole play (every change of the board, the phases and the court). */
function useHistory(initial: PlayDoc) {
  const [state, setState] = useState<Snap>({ doc: initial, idx: 0 });
  const past = useRef<Snap[]>([]);
  const future = useRef<Snap[]>([]);
  const pending = useRef<Snap | null>(null);
  const current = useRef(state);
  current.current = state;
  const [, rerender] = useState(0);

  const push = (s: Snap) => {
    past.current = [...past.current.slice(-HISTORY + 1), s];
    future.current = [];
  };
  /** a change that is one step of its own (a button) */
  const commit = useCallback((next: Snap) => {
    push(current.current);
    pending.current = null;
    setState(next);
    rerender((n) => n + 1);
  }, []);
  /** a board gesture starts: its first change records the state before it */
  const begin = useCallback(() => {
    pending.current = current.current;
  }, []);
  /** a change during a gesture (drag, drawing) or of a text field: no own step */
  const live = useCallback((next: Snap) => {
    if (pending.current) {
      push(pending.current);
      pending.current = null;
      rerender((n) => n + 1);
    }
    setState(next);
  }, []);
  const undo = useCallback(() => {
    const prev = past.current[past.current.length - 1];
    if (!prev) return;
    past.current = past.current.slice(0, -1);
    future.current = [current.current, ...future.current];
    setState(prev);
    rerender((n) => n + 1);
  }, []);
  const redo = useCallback(() => {
    const next = future.current[0];
    if (!next) return;
    future.current = future.current.slice(1);
    past.current = [...past.current, current.current];
    setState(next);
    rerender((n) => n + 1);
  }, []);
  return { state, commit, begin, live, undo, redo, canUndo: past.current.length > 0, canRedo: future.current.length > 0, select: (idx: number) => setState((s) => ({ ...s, idx })) };
}

/**
 * A play: the board is the main view. Everybody sees it big with play and pause and the phase
 * notes ("Ansehen"); staff switch to "Bearbeiten" to drag players like on a magnet board, draw runs,
 * passes, dribbles and screens, add phases and undo every step.
 */
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
  const confirm = useConfirm();
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const router = useRouter();
  const h = useHistory((play?.doc as unknown as PlayDoc | undefined) ?? initialDoc ?? EMPTY_DOC);
  const { doc, idx } = h.state;
  // a new play opens on the board to edit, a saved one to look at
  const [editing, setEditing] = useState(editable && !play);
  const edit = editable && editing;
  const [tool, setTool] = useState<Tool>("move");
  const [selected, setSelected] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [clock, setClock] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [big, setBig] = useState(false);
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
      // the step is taken outside the state updater (React may call an updater twice)
      const step = (now - last) * speed;
      last = now;
      setClock((c) => Math.min(total, c + step));
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [playing, speed, doc]);
  useEffect(() => {
    if (playing && clock >= totalDuration(doc)) setPlaying(false);
  }, [playing, clock, doc]);
  const live = playing || clock > 0 ? stateAt(doc, clock) : null;
  const shownIdx = live ? live.frame : idx;
  const shownFrame = doc.frames[shownIdx] ?? frame;

  const stop = () => (setPlaying(false), setClock(0));
  const change = (next: PlayDoc, to = idx, step = true) => {
    (step ? h.commit : h.live)({ doc: next, idx: Math.max(0, Math.min(to, next.frames.length - 1)) });
    setDirty(true);
    setNotice(null);
  };
  const setFrame = (f: Frame, step = true) => change({ ...doc, frames: doc.frames.map((x, i) => (i === idx ? f : x)) }, idx, step);

  // keyboard: undo and redo, Escape leaves the big view
  const { undo, redo } = h;
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (e.key === "Escape" && big) setBig(false);
      if (!edit || (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName))) return;
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      } else if (mod && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [edit, big, undo, redo]);

  // unsaved changes: the browser asks before leaving
  useEffect(() => {
    if (!dirty || !edit) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, edit]);

  function addToken(side: Side) {
    if (frame.tokens.length >= LIMITS.tokens) return;
    const used = new Set(frame.tokens.filter((k) => k.side === side).map((k) => k.label));
    let n = 1;
    while (used.has(String(n))) n++;
    let id = `${side[0]}${n}`;
    while (frame.tokens.some((k) => k.id === id)) id += "x";
    const around: [number, number] = doc.court === "half" ? (side === "own" ? [29, 10] : [33, 10]) : side === "own" ? [16, 10] : [24, 10];
    const [x, y] = freeSpot(frame.tokens, around);
    setFrame({ ...frame, tokens: [...frame.tokens, { id, side, label: String(n), x, y }] });
    setSelected(id);
    setTool("move");
  }

  const sel = frame.tokens.find((k) => k.id === selected) ?? null;
  const selArrow = selected?.startsWith("arrow:") ? Number(selected.slice(6)) : null;

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (validate(doc).length) {
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

  const segment = (on: boolean) =>
    cn("inline-flex min-h-11 items-center gap-1.5 border-2 px-3 text-[15px] font-semibold", on ? "border-ink bg-ink text-ground" : "border-ink/25 bg-paper text-ink hover:border-ink");

  // the tools stay in reach while the board scrolls under them (review R14); under the sticky
  // top bar of the app (62 px, 66 px from lg)
  const toolbar = edit && (
    <div className="sticky top-[62px] z-20 -mx-4 space-y-2 border-b border-rule bg-ground px-4 pt-2 pb-1 md:-mx-8 md:px-8 lg:top-[66px] lg:mx-0 lg:px-0">
      <div className="scrollbar-none -mx-1 flex gap-1 overflow-x-auto px-1 pb-1" role="toolbar" aria-label={t("tools")}>
        {TOOLS.map((k) => (
          <button key={k} type="button" aria-pressed={tool === k} onClick={() => setTool(k)} className={cn(segment(tool === k), "shrink-0")}>
            <ToolIcon tool={k} />
            {t(`tool_${k}`)}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-1">
        <Button variant="secondary" size="icon" aria-label={t("undo")} title={t("undo")} disabled={!h.canUndo} onClick={() => (stop(), h.undo())}>
          <Undo2 aria-hidden />
        </Button>
        <Button variant="secondary" size="icon" aria-label={t("redo")} title={t("redo")} disabled={!h.canRedo} onClick={() => (stop(), h.redo())}>
          <Redo2 aria-hidden />
        </Button>
        <span className="mx-1 h-8 w-px bg-rule" aria-hidden />
        <Button variant="secondary" size="sm" disabled={frame.tokens.length >= LIMITS.tokens} onClick={() => addToken("own")}>
          <Plus aria-hidden />
          {/* the colour of «Wir» and «Gegner» on the board, also while drawing (review R15) */}
          <TokenDot side="own" />
          {t("own")}
        </Button>
        <Button variant="secondary" size="sm" disabled={frame.tokens.length >= LIMITS.tokens} onClick={() => addToken("opp")}>
          <Plus aria-hidden />
          <TokenDot side="opp" />
          {t("opp")}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => change(mirrorDoc(doc))} title={t("mirrorHint")}>
          <FlipHorizontal2 aria-hidden />
          {t("mirror")}
        </Button>
        <div role="group" aria-label={t("court")} className="ml-auto flex">
          {(["half", "full"] as const).map((c) => (
            <button key={c} type="button" aria-pressed={doc.court === c} onClick={() => doc.court !== c && change({ ...doc, court: c })} className={cn(segment(doc.court === c), "-ml-0.5 first:ml-0")}>
              {t(`court_${c}`)}
            </button>
          ))}
        </div>
      </div>
      <p className="text-sm text-muted" aria-live="polite">
        {t(`hint_${tool}`)}
      </p>
    </div>
  );

  const timeline = (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        variant="primary"
        size="sm"
        onClick={() => {
          if (!playing && clock >= totalDuration(doc)) setClock(0);
          setSelected(null);
          setPlaying((p) => !p);
        }}
        disabled={doc.frames.length < 2}
      >
        {playing ? <Pause aria-hidden /> : <Play aria-hidden />}
        {playing ? t("pause") : t("play")}
      </Button>
      {(playing || clock > 0) && (
        <Button variant="ghost" size="sm" onClick={stop}>
          <RotateCcw aria-hidden />
          {t("stop")}
        </Button>
      )}
      <ol className="flex flex-wrap gap-1" aria-label={t("frames")}>
        {doc.frames.map((_, i) => (
          <li key={i}>
            <button
              type="button"
              aria-current={i === shownIdx ? "step" : undefined}
              onClick={() => (stop(), h.select(i), setSelected(null))}
              className={cn("size-11 border-2 text-[15px] font-semibold tabular-nums", i === shownIdx ? "border-ink bg-ink text-ground" : "border-ink/25 bg-paper hover:border-ink")}
            >
              {i + 1}
            </button>
          </li>
        ))}
      </ol>
      {edit && (
        <>
          <Button
            variant="secondary"
            size="sm"
            disabled={doc.frames.length >= LIMITS.frames}
            onClick={() => (stop(), setSelected(null), change({ ...doc, frames: [...doc.frames.slice(0, idx + 1), nextFrame(frame), ...doc.frames.slice(idx + 1)] }, idx + 1))}
          >
            + {t("frame")}
          </Button>
          <Button variant="ghost" size="sm" disabled={doc.frames.length <= 1} onClick={() => (stop(), setSelected(null), change({ ...doc, frames: doc.frames.filter((_, i) => i !== idx) }, idx - 1))}>
            <Trash2 aria-hidden />
            {t("deleteFrame")}
          </Button>
        </>
      )}
      <div role="group" aria-label={t("speed")} className="ml-auto flex">
        {SPEEDS.map((s) => (
          <button key={s} type="button" aria-pressed={speed === s} onClick={() => setSpeed(s)} className={cn("min-h-11 min-w-11 px-2 text-sm font-semibold", speed === s ? "bg-ink text-ground" : "text-ink-2 hover:text-ink")}>
            {String(s).replace(".", t("decimal"))}×
          </button>
        ))}
      </div>
    </div>
  );

  const empty = frame.tokens.length === 0 && !live;

  return (
    <div className="grid gap-x-8 gap-y-5 lg:grid-cols-[minmax(0,1fr)_19rem]">
      <div className="min-w-0 space-y-3">
        {editable && (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[15px] font-semibold">{edit ? t("editIntro") : t("viewIntro")}</p>
            {play && (
              <Button variant={edit ? "secondary" : "primary"} size="sm" onClick={() => (stop(), setSelected(null), setEditing((v) => !v))} aria-pressed={edit}>
                {edit ? <Eye aria-hidden /> : <Pencil aria-hidden />}
                {edit ? t("view") : t("edit")}
              </Button>
            )}
          </div>
        )}
        {toolbar}
        {/* the big view fills the screen; on a phone held across, the controls sit beside the board */}
        <div
          className={cn(big ? "fixed inset-0 z-50 flex flex-col gap-2 bg-background p-2 landscape:flex-row sm:p-4" : "space-y-3")}
          role={big ? "dialog" : undefined}
          aria-modal={big || undefined}
          aria-label={big ? t("board") : undefined}
        >
          <div className={cn("relative", big && "min-h-0 min-w-0 flex-1")}>
            <Board
              frame={shownFrame}
              live={live}
              court={doc.court}
              editable={edit && !live}
              tool={tool}
              selected={selected}
              onSelect={setSelected}
              onGestureStart={h.begin}
              onChange={(f) => setFrame(f, false)}
              label={play?.name ? `${t("board")}: ${play.name}` : t("board")}
              className={big ? "h-full" : "h-auto max-h-[78svh]"}
            />
            {empty && edit && (
              <p className="pointer-events-none absolute inset-x-4 top-1/2 -translate-y-1/2 bg-paper/95 p-3 text-center text-[15px] ring-1 ring-ink/20">{t("emptyBoard")}</p>
            )}
            {big ? (
              <Button variant="secondary" size="icon" className="absolute top-2 right-2 bg-paper" aria-label={t("bigClose")} title={t("bigClose")} onClick={() => setBig(false)}>
                <Minimize2 aria-hidden />
              </Button>
            ) : (
              <Button variant="secondary" size="icon" className="absolute right-2 bottom-2 bg-paper" aria-label={t("big")} title={t("big")} onClick={() => setBig(true)}>
                <Maximize2 aria-hidden />
              </Button>
            )}
          </div>
          <div className={cn(big ? "flex shrink-0 flex-col gap-2 overflow-auto landscape:w-72" : "space-y-3")}>
            {timeline}
            {(live ? shownFrame.note : !edit && frame.note) && (
              <p className="border-l-4 border-ink bg-paper px-3 py-2 text-[15px]" aria-live="polite">
                <span className="font-semibold">{t("phaseOf", { n: shownIdx + 1, total: doc.frames.length })}: </span>
                {shownFrame.note}
              </p>
            )}
          </div>
        </div>
        {!edit && <Legend />}
        {edit && (
          <div className="grid gap-3 sm:grid-cols-[1fr_10rem]">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t("note")}</span>
              <textarea
                value={frame.note}
                maxLength={LIMITS.note}
                rows={2}
                onFocus={h.begin}
                onChange={(e) => setFrame({ ...frame, note: e.target.value }, false)}
                className="bg-raised px-2 py-1 ring-1 ring-inset ring-border"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t("duration")}</span>
              <select value={frame.duration_ms} onChange={(e) => setFrame({ ...frame, duration_ms: Number(e.target.value) })} className="min-h-11 bg-raised px-2 ring-1 ring-inset ring-border">
                {[1000, 1500, 2000, 3000, 4000, 6000].map((ms) => (
                  <option key={ms} value={ms}>
                    {String(ms / 1000).replace(".", t("decimal"))} s
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
        {edit && (sel || (selArrow != null && frame.arrows[selArrow]) || (selected === "ball" && frame.ball)) && (
          <div className="flex flex-wrap items-end gap-2 bg-paper p-3 text-sm ring-1 ring-ink/15" aria-live="polite">
            {sel && (
              <>
                <label className="flex flex-col gap-1">
                  <span className="font-medium">{t("label")}</span>
                  <input
                    value={sel.label}
                    maxLength={3}
                    onFocus={h.begin}
                    onChange={(e) => setFrame({ ...frame, tokens: frame.tokens.map((k) => (k.id === sel.id ? { ...k, label: e.target.value } : k)) }, false)}
                    className="min-h-11 w-20 bg-raised px-2 ring-1 ring-inset ring-border"
                  />
                </label>
                <Button variant="ghost" size="sm" onClick={() => (setFrame({ ...frame, tokens: frame.tokens.filter((k) => k.id !== sel.id) }), setSelected(null))}>
                  <Trash2 aria-hidden />
                  {t("removeToken")}
                </Button>
              </>
            )}
            {selArrow != null && frame.arrows[selArrow] && (
              <>
                <p className="flex min-h-11 items-center gap-2 font-medium">
                  <ToolIcon tool={frame.arrows[selArrow]!.kind} />
                  {t(`tool_${frame.arrows[selArrow]!.kind}`)}
                </p>
                <Button variant="ghost" size="sm" onClick={() => (setFrame({ ...frame, arrows: frame.arrows.filter((_, i) => i !== selArrow) }), setSelected(null))}>
                  <Trash2 aria-hidden />
                  {t("removeArrow")}
                </Button>
              </>
            )}
            {selected === "ball" && frame.ball && (
              <Button variant="ghost" size="sm" onClick={() => (setFrame({ ...frame, ball: null }), setSelected(null))}>
                <Trash2 aria-hidden />
                {t("removeBall")}
              </Button>
            )}
            <p className="basis-full text-muted">{t("keyboardHint")}</p>
          </div>
        )}
      </div>

      <Card className="h-fit space-y-3">
        {edit ? (
          <form onSubmit={save} className="space-y-3" aria-label={t("details")}>
            <Input label={t("name")} name="name" required maxLength={120} defaultValue={play?.name ?? initialMeta?.name ?? ""} />
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">{t("category")}</span>
              <select name="category" defaultValue={play?.category ?? initialMeta?.category ?? "attack"} className="min-h-11 bg-raised px-2 ring-1 ring-inset ring-border">
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
              <textarea name="description" rows={3} maxLength={4000} defaultValue={play?.description ?? ""} className="bg-raised px-2 py-1 ring-1 ring-inset ring-border" />
            </label>
            <label className="flex min-h-11 items-center gap-2 text-sm">
              <input type="checkbox" name="shared" defaultChecked={play?.shared_with_players ?? false} className="size-5" />
              {t("shared")}
            </label>
            <Button type="submit" className="w-full">
              {t("save")}
            </Button>
            {dirty && <p className="text-sm text-muted">{t("unsaved")}</p>}
            {play && (
              <Button
                variant="danger"
                className="w-full"
                onClick={async () => {
                  if (!(await confirm({ title: t("deleteConfirm"), danger: true }))) return;
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
            <h2 className="text-lg font-semibold">{play?.name ?? initialMeta?.name}</h2>
            <p className="text-muted">
              {t(`cat_${(play?.category ?? initialMeta?.category ?? "other") as "other"}`)}
              {(play?.formation ?? initialMeta?.formation) && ` · ${play?.formation ?? initialMeta?.formation}`} · {t("frames_count", { count: doc.frames.length })}
            </p>
            {play?.description && <p className="whitespace-pre-line text-[15px]">{play.description}</p>}
          </div>
        )}
        {source && (
          <a className="block text-sm font-medium text-accent underline decoration-[1.5px] underline-offset-4" href={`/app/${orgId}/matches/${source.match_id}?t=${source.t_ms}`}>
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

/** What the marks on the board mean (for players who see a play for the first time). */
export function Legend({ className }: { className?: string }) {
  const t = useTranslations("tactics");
  const item = (icon: ReactNode, text: string) => (
    <li key={text} className="flex items-center gap-2">
      {icon}
      {text}
    </li>
  );
  return (
    <ul className={cn("flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-2", className)} aria-label={t("legend")}>
      {item(<TokenDot side="own" />, t("own"))}
      {item(<TokenDot side="opp" />, t("opp"))}
      {(["run", "pass", "dribble", "screen"] as const).map((k) => item(<ToolIcon tool={k} />, t(`tool_${k}`)))}
    </ul>
  );
}

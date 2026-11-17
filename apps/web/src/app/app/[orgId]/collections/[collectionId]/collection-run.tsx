"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { Fragment } from "react";
import { useTranslations } from "next-intl";
import { ArrowDown, ArrowUp, MoreHorizontal, StickyNote, Trash2 } from "lucide-react";
import { Bundle, EmptyField } from "@/components/anlauf/bundle";
import { MenuContent, MenuItem, MenuRoot, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { clockOf } from "@/components/anlauf/three-things-view";
import { goalRuns, useMatchGraphics } from "@/lib/graphics";

type Item = Schemas["ItemOut"];

const time = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.round((ms % 60000) / 1000)).padStart(2, "0")}`;

/** Moving and removing an entry (the coach trims the draft, UX test B05). */
export interface RunEdit {
  move: (index: number, by: -1 | 1) => void;
  remove: (index: number) => void;
  /** a note right after this entry (UX test N29) */
  noteAfter: (index: number) => void;
}

/** The run of a collection (SPEC 7.7): numbered scenes with their Minifeld, plays and notes. */
export function CollectionRun({ orgId, items, edit, slot }: { orgId: string; items: Item[]; edit?: RunEdit; slot?: { after: number; node: React.ReactNode } | null }) {
  const t = useTranslations("collections");
  const tools = (n: number) => (edit ? <RowTools n={n} last={items.length - 1} edit={edit} /> : null);
  return (
    <ol className="m-0 list-none p-0" data-testid="collection-items">
      {items.map((i, n) => (
        <Fragment key={i.position}>
        {i.kind === "note" && !i.scene && !i.play ? (
          <li key={i.position} className="grid grid-cols-[40px_minmax(0,1fr)] items-center gap-4 border-t border-rule py-3.5" data-testid="collection-item">
            <b className="font-num text-[26px] text-ink-2">{n + 1}</b>
            <div className="min-w-0">
              <p className="m-0 border-l-4 border-club-text pl-3 text-[17px] whitespace-pre-line italic">{i.text}</p>
              {tools(n)}
            </div>
          </li>
        ) : i.play ? (
          <li key={i.position} className="grid grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-4 border-t border-rule py-3.5" data-testid="collection-item">
            <b className="font-num text-[26px] text-ink-2">{n + 1}</b>
            <div className="min-w-0">
              <Link href={`/app/${orgId}/plays/${i.play.id}`} className="text-[17px] font-bold text-ink no-underline hover:underline">
                {t("playPrefix")}: {i.play.name}
              </Link>
              {i.text && <p className="m-0 text-[15px] text-ink-2">{i.text}</p>}
              {tools(n)}
            </div>
            <span className="font-mono text-[13px] font-semibold text-ink">{t("drawn")}</span>
          </li>
        ) : i.scene ? (
          <SceneRow key={i.position} orgId={orgId} n={n + 1} item={i} scene={i.scene} tools={tools(n)} />
        ) : null}
        {slot && slot.after === n && <li className="border-t border-rule py-3.5">{slot.node}</li>}
        </Fragment>
      ))}
    </ol>
  );
}

/** Compact at phone width (24 scenes are a long list): up, down and «…» with the note and
 * removing. Every button is named for screen readers with the entry's number. */
function RowTools({ n, last, edit }: { n: number; last: number; edit: RunEdit }) {
  const t = useTranslations("collections");
  const b =
    "inline-flex size-11 cursor-pointer items-center justify-center bg-transparent text-ink hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent disabled:cursor-default disabled:text-ink-2/50 disabled:hover:bg-transparent [&_svg]:size-5";
  return (
    <span className="mt-1 -ml-2.5 flex items-center">
      <button type="button" className={b} disabled={n === 0} onClick={() => edit.move(n, -1)} aria-label={t("moveUpItem", { n: n + 1 })} title={t("moveUp")}>
        <ArrowUp aria-hidden />
      </button>
      <button type="button" className={b} disabled={n === last} onClick={() => edit.move(n, 1)} aria-label={t("moveDownItem", { n: n + 1 })} title={t("moveDown")}>
        <ArrowDown aria-hidden />
      </button>
      <MenuRoot>
        <MenuTrigger asChild>
          <button type="button" className={b} aria-label={t("moreItem", { n: n + 1 })} title={t("more")} data-testid="item-more">
            <MoreHorizontal aria-hidden />
          </button>
        </MenuTrigger>
        <MenuContent align="start">
          <MenuItem icon={<StickyNote />} onSelect={() => edit.noteAfter(n)} testId="item-note-after">
            {t("noteHere")}
          </MenuItem>
          <MenuSeparator />
          {/* apart from the rest: a slip is undone with «Rückgängig» (UX test N30) */}
          <MenuItem icon={<Trash2 />} danger onSelect={() => edit.remove(n)} testId="item-remove">
            {t("remove")}
          </MenuItem>
        </MenuContent>
      </MenuRoot>
    </span>
  );
}

function SceneRow({ orgId, n, item, scene, tools }: { orgId: string; n: number; item: Item; scene: Schemas["SceneOut"]; tools?: React.ReactNode }) {
  const t = useTranslations("collections");
  const g = useMatchGraphics(orgId, scene.match_id);
  // the goal the scene was made from: its run is the Minifeld, its minute and zone the title
  const goal = g.data && scene.event_id ? goalRuns(g.data).find((x) => x.eventId === scene.event_id) : undefined;
  const title = goal
    ? `${goal.minute != null ? `${clockOf(goal.minute)} ` : ""}${goal.team === "opp" ? t("goalAgainst") : t("goalFor")}${goal.zone ? ` ${t(`sceneZone.${goal.zone}` as "sceneZone.la")}` : ""}`
    : scene.title || t("scene");
  return (
    <li className="grid grid-cols-[40px_84px_minmax(0,1fr)_auto] items-center gap-4 border-t border-rule py-3.5 md:grid-cols-[40px_112px_minmax(0,1fr)_auto]" data-testid="collection-item">
      <b className="font-num text-[26px] text-ink-2">{n}</b>
      <span aria-hidden>{goal ? <Bundle goals={[goal]} width={112} label="" /> : <EmptyField />}</span>
      <div className="min-w-0">
        <Link href={`/app/${orgId}/matches/${scene.match_id}?tab=video&t=${scene.start_ms}`} className="text-[17px] font-bold text-ink no-underline hover:underline">
          {title}
        </Link>
        {item.text && <p className="m-0 text-[15px] text-ink-2">{item.text}</p>}
        {tools}
      </div>
      <span className="font-mono text-[13px] font-semibold text-ink">{time(Math.max(0, scene.end_ms - scene.start_ms))}</span>
    </li>
  );
}

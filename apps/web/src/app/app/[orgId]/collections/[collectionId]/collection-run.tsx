"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Bundle, EmptyField } from "@/components/anlauf/bundle";
import { clockOf } from "@/components/anlauf/three-things-view";
import { goalRuns, useMatchGraphics } from "@/lib/graphics";

type Item = Schemas["ItemOut"];

const time = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.round((ms % 60000) / 1000)).padStart(2, "0")}`;

/** Moving and removing an entry (the coach trims the draft, UX test B05). */
export interface RunEdit {
  move: (index: number, by: -1 | 1) => void;
  remove: (index: number) => void;
}

/** The run of a collection (SPEC 7.7): numbered scenes with their Minifeld, plays and notes. */
export function CollectionRun({ orgId, items, edit }: { orgId: string; items: Item[]; edit?: RunEdit }) {
  const t = useTranslations("collections");
  const tools = (n: number) => (edit ? <RowTools n={n} last={items.length - 1} edit={edit} /> : null);
  return (
    <ol className="m-0 list-none p-0" data-testid="collection-items">
      {items.map((i, n) =>
        i.kind === "note" && !i.scene && !i.play ? (
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
            <span className="font-mono text-[13px] font-semibold text-ink-2">{t("drawn")}</span>
          </li>
        ) : i.scene ? (
          <SceneRow key={i.position} orgId={orgId} n={n + 1} item={i} scene={i.scene} tools={tools(n)} />
        ) : null,
      )}
    </ol>
  );
}

function RowTools({ n, last, edit }: { n: number; last: number; edit: RunEdit }) {
  const t = useTranslations("collections");
  const b = "min-h-11 cursor-pointer bg-transparent px-1 text-[13px] font-bold text-ink underline decoration-[1.5px] underline-offset-4 disabled:cursor-default disabled:text-ink-2 disabled:no-underline";
  return (
    <span className="mt-1 flex flex-wrap gap-x-3">
      <button type="button" className={b} disabled={n === 0} onClick={() => edit.move(n, -1)}>
        {t("moveUp")}
      </button>
      <button type="button" className={b} disabled={n === last} onClick={() => edit.move(n, 1)}>
        {t("moveDown")}
      </button>
      <button type="button" className={b} onClick={() => edit.remove(n)} data-testid="item-remove">
        {t("remove")}
      </button>
    </span>
  );
}

function SceneRow({ orgId, n, item, scene, tools }: { orgId: string; n: number; item: Item; scene: Schemas["SceneOut"]; tools?: React.ReactNode }) {
  const t = useTranslations("collections");
  const g = useMatchGraphics(orgId, scene.match_id);
  const ta = useTranslations("anlauf");
  // the goal the scene was made from: its run is the Minifeld, its minute and zone the title
  const goal = g.data && scene.event_id ? goalRuns(g.data).find((x) => x.eventId === scene.event_id) : undefined;
  const title = goal
    ? `${goal.minute != null ? `${clockOf(goal.minute)} ` : ""}${goal.team === "opp" ? t("goalAgainst") : t("goalFor")}${goal.zone ? ` ${ta(`zoneFrom.${goal.zone}` as "zoneFrom.la")}` : ""}`
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
      <span className="font-mono text-[13px] font-semibold text-ink-2">{time(Math.max(0, scene.end_ms - scene.start_ms))}</span>
    </li>
  );
}

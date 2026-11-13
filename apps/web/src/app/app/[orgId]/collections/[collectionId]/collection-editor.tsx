"use client";

import type { Schemas } from "@handball/api-client";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";
import { CollectionRun } from "./collection-run";

type Collection = Schemas["CollectionOut"];
type Item = Schemas["ItemOut"];
type ItemIn = Schemas["ItemIn"];

/** An entry as it goes back to the API: a scene keeps its clip, a play its play, a note its text. */
function toIn(i: Item): ItemIn {
  if (i.scene) return { kind: "scene", clip_id: i.scene.clip_id, text: i.text ?? null };
  if (i.play) return { kind: "play", play_id: i.play.id, text: i.text ?? null };
  return { kind: "note", text: i.text ?? "" };
}

/**
 * The run of a collection the coach can change (SPEC 7.7, UX test B05): the title by a tap, each
 * entry up, down or away, a note at the end. Every change is saved at once.
 */
export function CollectionEditor({ orgId, collection }: { orgId: string; collection: Collection }) {
  const t = useTranslations("collections");
  const router = useRouter();
  const [items, setItems] = useState<Item[]>(collection.items);
  const [note, setNote] = useState<string | null>(null);
  // where a new note goes: after this entry, or at the end (UX test N29)
  const [noteAt, setNoteAt] = useState<number | null>(null);
  // the entry just removed, for «Rückgängig» during a few seconds (UX test N30)
  const [undo, setUndo] = useState<{ item: Item; index: number } | null>(null);
  useEffect(() => {
    if (!undo) return;
    const id = window.setTimeout(() => setUndo(null), 7000);
    return () => window.clearTimeout(id);
  }, [undo]);
  const [saving, setSaving] = useState(false);
  const path = { params: { path: { org_id: orgId, collection_id: collection.id } } };

  // changes are saved one after the other, in the order they were made; only the last answer
  // replaces the list (two quick taps never undo each other)
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const latest = useRef(0);
  function save(next: Item[], extra?: ItemIn, at = next.length): Promise<unknown> {
    const n = ++latest.current;
    setSaving(true);
    const list = next.map(toIn);
    if (extra) list.splice(at, 0, extra);
    const body = { items: list };
    queue.current = queue.current.then(async () => {
      const { data } = await api.PATCH("/v1/orgs/{org_id}/collections/{collection_id}", { ...path, body });
      if (n === latest.current) {
        setSaving(false);
        if (data) setItems(data.items);
        router.refresh();
      }
    });
    return queue.current;
  }
  const edit = {
    move: (i: number, by: -1 | 1) => {
      const next = [...items];
      const [x] = next.splice(i, 1);
      next.splice(i + by, 0, x!);
      setItems(next);
      void save(next);
    },
    remove: (i: number) => {
      const next = items.filter((_, k) => k !== i);
      setUndo({ item: items[i]!, index: i });
      setItems(next);
      void save(next);
    },
    noteAfter: (i: number) => {
      setNoteAt(i + 1);
      setNote("");
    },
  };
  function takeBack() {
    if (!undo) return;
    const next = [...items];
    next.splice(undo.index, 0, undo.item);
    setUndo(null);
    setItems(next);
    void save(next);
  }

  const form = (
    <form
      className="space-y-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!note?.trim()) return;
        void save(items, { kind: "note", text: note.trim() }, noteAt ?? items.length).then(() => (setNote(null), setNoteAt(null)));
      }}
    >
      <label className="block text-[15px] font-semibold text-ink-2" htmlFor="new-note">
        {t("noteLabel")}
      </label>
      <textarea id="new-note" value={note ?? ""} onChange={(e) => setNote(e.target.value)} rows={3} maxLength={2000} autoFocus className="w-full border-2 border-ink bg-paper p-3 text-[17px]" />
      <div className="flex gap-2.5">
        <Button type="submit" size="sm" loading={saving} disabled={!note?.trim()}>
          {t("saveNote")}
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={() => (setNote(null), setNoteAt(null))}>
          {t("cancel")}
        </Button>
      </div>
    </form>
  );
  const inline = note != null && noteAt != null && noteAt < items.length;
  return (
    <div aria-busy={saving} data-testid="collection-editor">
      {undo && (
        <p role="status" className="sticky top-2 z-10 m-0 mb-3 flex flex-wrap items-center gap-3 border-2 border-ink bg-ground px-3 py-2 text-[17px]" data-testid="undo-remove">
          {t("removed")}
          <button type="button" onClick={takeBack} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 font-bold text-ink underline decoration-[1.5px] underline-offset-4">
            {t("undo")}
          </button>
        </p>
      )}
      {items.length === 0 ? <p className="text-[17px] text-ink-2">{t("empty")}</p> : <CollectionRun orgId={orgId} items={items} edit={collection.editable ? edit : undefined} slot={inline ? { after: noteAt - 1, node: form } : null} />}
      {collection.editable && (
        <div className="mt-4">
          {note == null ? (
            <Button variant="secondary" size="sm" onClick={() => (setNoteAt(null), setNote(""))} data-testid="add-note">
              {t("addNote")}
            </Button>
          ) : inline ? null : (
            form
          )}
        </div>
      )}
    </div>
  );
}

/** The title of a collection: a tap makes it editable, Enter saves (UX test B05). */
export function CollectionTitle({ orgId, collection }: { orgId: string; collection: Collection }) {
  const t = useTranslations("collections");
  const router = useRouter();
  const [title, setTitle] = useState(collection.title);
  const [editing, setEditing] = useState(false);
  if (!collection.editable) return <>{title}</>;
  if (!editing) {
    return (
      <button type="button" onClick={() => setEditing(true)} className="cursor-text bg-transparent p-0 text-left text-[length:inherit] leading-[inherit] text-inherit" title={t("rename")} data-testid="collection-title">
        {title}
      </button>
    );
  }
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        const next = title.trim();
        if (!next) return;
        await api.PATCH("/v1/orgs/{org_id}/collections/{collection_id}", { params: { path: { org_id: orgId, collection_id: collection.id } }, body: { title: next } });
        setEditing(false);
        router.refresh();
      }}
    >
      <label className="sr-only" htmlFor="collection-title-input">
        {t("rename")}
      </label>
      <input
        id="collection-title-input"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={(e) => e.currentTarget.form?.requestSubmit()}
        maxLength={200}
        autoFocus
        className="w-full border-b-2 border-ink bg-transparent text-[length:inherit] leading-[inherit] outline-none"
      />
    </form>
  );
}

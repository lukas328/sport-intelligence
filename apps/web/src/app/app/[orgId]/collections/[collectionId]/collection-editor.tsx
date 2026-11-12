"use client";

import type { Schemas } from "@handball/api-client";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
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
  const [saving, setSaving] = useState(false);
  const path = { params: { path: { org_id: orgId, collection_id: collection.id } } };

  // changes are saved one after the other, in the order they were made; only the last answer
  // replaces the list (two quick taps never undo each other)
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const latest = useRef(0);
  function save(next: Item[], extra?: ItemIn): Promise<unknown> {
    const n = ++latest.current;
    setSaving(true);
    const body = { items: [...next.map(toIn), ...(extra ? [extra] : [])] };
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
      setItems(next);
      void save(next);
    },
  };

  return (
    <div aria-busy={saving} data-testid="collection-editor">
      {items.length === 0 ? <p className="text-[17px] text-ink-2">{t("empty")}</p> : <CollectionRun orgId={orgId} items={items} edit={collection.editable ? edit : undefined} />}
      {collection.editable && (
        <div className="mt-4">
          {note == null ? (
            <Button variant="secondary" size="sm" onClick={() => setNote("")} data-testid="add-note">
              {t("addNote")}
            </Button>
          ) : (
            <form
              className="space-y-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (!note.trim()) return;
                void save(items, { kind: "note", text: note.trim() }).then(() => setNote(null));
              }}
            >
              <label className="block text-[13px] font-semibold text-ink-2" htmlFor="new-note">
                {t("noteLabel")}
              </label>
              <textarea id="new-note" value={note} onChange={(e) => setNote(e.target.value)} rows={3} maxLength={2000} autoFocus className="w-full border-2 border-ink bg-paper p-3 text-[17px]" />
              <div className="flex gap-2.5">
                <Button type="submit" size="sm" loading={saving} disabled={!note.trim()}>
                  {t("saveNote")}
                </Button>
                <Button type="button" variant="ghost" size="sm" onClick={() => setNote(null)}>
                  {t("cancel")}
                </Button>
              </div>
            </form>
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

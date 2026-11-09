"use client";

import type { Schemas } from "@handball/api-client";
import { TEMPLATES, searchTemplates, type PlayDoc } from "@handball/tactics";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { Board } from "@/components/tactics/board";
import { EmptyState } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { buttonClass } from "@/components/ui/button";

const CATEGORIES = ["attack", "defence", "fast_break", "set_piece", "seven_m", "other"] as const;

export function PlayLibrary({ orgId, teamId, plays, staff }: { orgId: string; teamId: string; plays: Schemas["PlayOut"][]; staff: boolean }) {
  const t = useTranslations("tactics");
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<string>("");
  const needle = q.trim().toLowerCase();
  const list = useMemo(
    () =>
      plays.filter(
        (p) =>
          (!cat || p.category === cat) &&
          (!needle || p.name.toLowerCase().includes(needle) || (p.formation ?? "").toLowerCase().includes(needle) || p.tags.some((g) => g.toLowerCase().includes(needle))),
      ),
    [plays, cat, needle],
  );
  const templates = staff ? searchTemplates(q, (cat || undefined) as (typeof TEMPLATES)[number]["category"] | undefined) : [];
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3">
        {/* search and filters only when there is something to search: own plays, or the templates for staff */}
        {(plays.length > 0 || staff) && (
        <>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">{t("search")}</span>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="min-h-10 w-64 rounded-md bg-raised ring-1 ring-inset ring-border px-3"
          />
        </label>
        <div role="group" aria-label={t("category")} className="flex flex-wrap gap-x-4">
          {["", ...CATEGORIES].map((c) => (
            <button
              key={c || "all"}
              aria-pressed={cat === c}
              onClick={() => setCat(c)}
              className={cn("min-h-9 border-b-2 px-1 text-sm font-semibold", cat === c ? "border-foreground text-foreground" : "border-transparent text-muted hover:text-foreground")}
            >
              {c ? t(`cat_${c}`) : t("all")}
            </button>
          ))}
        </div>
        </>
        )}
        {staff && (
          <Link href={`/app/${orgId}/teams/${teamId}/plays/new`} className={cn(buttonClass("primary", "sm"), "ml-auto")}>
            {t("new")}
          </Link>
        )}
      </div>

      {list.length === 0 ? (
        <EmptyState title={t("empty")}>{staff && t("emptyHint")}</EmptyState>
      ) : (
        <ul className="grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-3" data-testid="play-list">
          {list.map((p) => (
            <li key={p.id}>
              <Link href={`/app/${orgId}/plays/${p.id}`} className="block space-y-2 border-t-2 border-foreground pt-2 hover:text-accent">
                <Preview doc={p.doc as unknown as PlayDoc} label={p.name} />
                <p className="font-medium">{p.name}</p>
                <p className="text-sm text-muted">
                  {t(`cat_${p.category as "other"}`)}
                  {p.formation && ` · ${p.formation}`} · {t("frames_count", { count: (p.doc as unknown as PlayDoc).frames.length })}
                  {p.shared_with_players && ` · ${t("sharedBadge")}`}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {templates.length > 0 && (
        <section className="space-y-3" aria-label={t("templates")}>
          <h2 className="text-lg font-semibold">{t("templates")}</h2>
          <ul className="grid gap-x-6 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">
            {templates.map((tpl) => (
              <li key={tpl.id}>
                <Link
                  href={`/app/${orgId}/teams/${teamId}/plays/new?template=${tpl.id}`}
                  className="block space-y-2 border-t border-foreground/30 pt-2 hover:text-accent"
                  aria-label={`${t("fromTemplate")}: ${t(`tpl_${tpl.id}`)}`}
                >
                  <Preview doc={tpl.doc} label={t(`tpl_${tpl.id}`)} />
                  <p className="text-sm font-medium">{t(`tpl_${tpl.id}`)}</p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Preview({ doc, label }: { doc: PlayDoc; label: string }) {
  const f = doc.frames[0];
  if (!f) return null;
  return (
    <div aria-hidden className="pointer-events-none">
      <Board frame={f} court={doc.court} label={label} />
    </div>
  );
}

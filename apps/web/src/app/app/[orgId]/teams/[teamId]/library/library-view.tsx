"use client";

import type { Schemas } from "@handball/api-client";
import type { PlayDoc } from "@handball/tactics";
import { ArrowRight, Plus, ScanSearch } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { Board } from "@/components/tactics/board";
import { cn } from "@/lib/utils";

type Play = Schemas["PlayOut"];
type Playlist = Schemas["PlaylistOut"];
type Presentation = Schemas["PresentationOut"];

const newest = <T extends { created_at: string }>(xs: T[]) => [...xs].sort((a, b) => b.created_at.localeCompare(a.created_at));

/** The team's own material, newest first: the library is its content, not a menu of icons. */
export function LibraryView({ base, orgBase, plays, playlists, presentations }: { base: string; orgBase: string; plays: Play[]; playlists: Playlist[]; presentations: Presentation[] }) {
  const t = useTranslations("library");
  const tt = useTranslations("tactics");
  const format = useFormatter();
  const when = (iso: string) => format.relativeTime(new Date(iso));
  return (
    <div className="space-y-12">
      <Link href={`${base}/search`} className="group flex items-center gap-4 rounded-2xl bg-foreground px-5 py-4 text-background transition-transform hover:-translate-y-px sm:px-6">
        <ScanSearch aria-hidden className="size-5 shrink-0 opacity-80" />
        <span className="min-w-0 flex-1">
          <span className="block font-semibold font-wide">{t("search")}</span>
          <span className="block truncate text-sm opacity-70">{t("searchHint")}</span>
        </span>
        <ArrowRight aria-hidden className="size-5 shrink-0 transition-transform group-hover:translate-x-1" />
      </Link>

      <Shelf title={t("plays")} href={`${base}/plays`} newHref={`${base}/plays/new`} count={plays.length}>
        {plays.length === 0 ? (
          <Empty>{t("emptyPlays")}</Empty>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {newest(plays)
              .slice(0, 4)
              .map((p) => {
                const doc = p.doc as unknown as PlayDoc;
                const frame = doc.frames?.[0];
                return (
                  <li key={p.id}>
                    <Link href={`${orgBase}/plays/${p.id}`} className="group block overflow-hidden rounded-2xl bg-raised ring-1 ring-border/70 transition-shadow hover:shadow-md">
                      <div aria-hidden className="pointer-events-none border-b border-border/70">
                        {frame && <Board frame={frame} court={doc.court} label={p.name} />}
                      </div>
                      <div className="px-4 py-3">
                        <p className="truncate font-semibold">{p.name}</p>
                        <p className="truncate text-[0.8125rem] text-muted">
                          {[tt(`cat_${p.category}` as "cat_attack"), (doc.frames?.length ?? 0) > 1 ? tt("frames_count", { count: doc.frames.length }) : null].filter(Boolean).join(" · ")}
                        </p>
                      </div>
                    </Link>
                  </li>
                );
              })}
          </ul>
        )}
      </Shelf>

      <div className="grid gap-12 lg:grid-cols-2 lg:gap-8">
        <Shelf title={t("playlists")} href={`${base}/playlists`} count={playlists.length}>
          {playlists.length === 0 ? (
            <Empty>{t("emptyPlaylists")}</Empty>
          ) : (
            <Rows>
              {newest(playlists)
                .slice(0, 5)
                .map((p) => (
                  <Row key={p.id} href={`${orgBase}/playlists/${p.id}`} title={p.title} meta={[t("clips", { n: p.item_count }), p.shared_with_players ? t("shared") : null, when(p.created_at)]} />
                ))}
            </Rows>
          )}
        </Shelf>
        <Shelf title={t("presentations")} href={`${base}/presentations`} count={presentations.length}>
          {presentations.length === 0 ? (
            <Empty>{t("emptyPresentations")}</Empty>
          ) : (
            <Rows>
              {newest(presentations)
                .slice(0, 5)
                .map((p) => (
                  <Row key={p.id} href={`${orgBase}/presentations/${p.id}`} title={p.title} meta={[t("slides", { n: p.slides }), p.shared_with_players ? t("shared") : null, when(p.created_at)]} />
                ))}
            </Rows>
          )}
        </Shelf>
      </div>
    </div>
  );
}

function Shelf({ title, href, newHref, count, children }: { title: string; href: string; newHref?: string; count: number; children: ReactNode }) {
  const t = useTranslations("library");
  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 border-b border-border/70 pb-3">
        <h2 className="text-lg font-bold">
          <Link href={href} className="hover:text-accent">
            {title}
          </Link>
          <span className="ml-2 text-sm font-medium text-muted tabular-nums">{count}</span>
        </h2>
        <div className="flex items-center gap-4 text-sm">
          {newHref && (
            <Link href={newHref} className="inline-flex items-center gap-1 font-medium text-muted hover:text-foreground">
              <Plus aria-hidden className="size-4" />
              {t("new")}
            </Link>
          )}
          <Link href={href} className="inline-flex items-center gap-1 font-medium text-accent hover:underline" aria-label={`${t("all")}: ${title}`}>
            {t("all")}
            <ArrowRight aria-hidden className="size-3.5" />
          </Link>
        </div>
      </div>
      {children}
    </section>
  );
}

function Rows({ children }: { children: ReactNode }) {
  return <ul className="divide-y divide-border/70">{children}</ul>;
}

function Row({ href, title, meta }: { href: string; title: string; meta: (string | null)[] }) {
  return (
    <li>
      <Link href={href} className="group flex items-center gap-3 py-3">
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium group-hover:text-accent">{title}</span>
          <span className="block truncate text-[0.8125rem] text-muted">{meta.filter(Boolean).join(" · ")}</span>
        </span>
        <ArrowRight aria-hidden className="size-4 shrink-0 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
      </Link>
    </li>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className={cn("max-w-prose text-sm text-muted")}>{children}</p>;
}

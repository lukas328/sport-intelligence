"use client";

import type { Schemas } from "@handball/api-client";
import { ArrowRight, ScanSearch } from "lucide-react";
import Link from "next/link";
import { useFormatter, useNow, useTranslations } from "next-intl";
import type { ReactNode } from "react";

type Playlist = Schemas["PlaylistOut"];
type Presentation = Schemas["PresentationOut"];

const newest = <T extends { created_at: string }>(xs: T[]) => [...xs].sort((a, b) => b.created_at.localeCompare(a.created_at));

/** Material from the matches, newest first: scene search, playlists, presentations (plays live in Training). */
export function LibraryView({ base, orgBase, playlists, presentations }: { base: string; orgBase: string; playlists: Playlist[]; presentations: Presentation[] }) {
  const t = useTranslations("library");
  const format = useFormatter();
  // relative times ("vor 5 Minuten") against a clock that moves on each minute
  const now = useNow({ updateInterval: 60_000 });
  const when = (iso: string) => format.relativeTime(new Date(iso), now);
  return (
    <div className="space-y-12">
      {/* the way into every scene of the season: a plain row, not a black banner */}
      <Link href={`${base}/scenes`} className="group flex items-center gap-4 border-y-2 border-foreground py-4">
        <ScanSearch aria-hidden className="size-5 shrink-0" />
        <span className="min-w-0 flex-1">
          <span className="block text-lg font-bold group-hover:underline group-hover:underline-offset-4">{t("search")}</span>
          <span className="block text-sm text-muted">{t("searchHint")}</span>
        </span>
        <ArrowRight aria-hidden className="size-5 shrink-0 transition-transform group-hover:translate-x-1" />
      </Link>

      <div className="grid gap-12 lg:grid-cols-2 lg:gap-8">
        <Shelf title={t("playlists")} href={`${base}/playlists`} count={playlists.length}>
          {playlists.length === 0 ? (
            <Empty href={`${base}/playlists`} action={t("newPlaylist")}>{t("emptyPlaylists")}</Empty>
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
            <Empty href={`${base}/presentations`} action={t("newPresentation")}>{t("emptyPresentations")}</Empty>
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

function Shelf({ title, href, count, children }: { title: string; href: string; count: number; children: ReactNode }) {
  const t = useTranslations("library");
  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 border-b border-foreground/15 pb-3">
        <h2 className="text-lg font-bold">
          <Link href={href} className="hover:underline hover:underline-offset-4">
            {title}
          </Link>
          {count > 0 && <span className="ml-2 text-sm font-medium text-muted tabular-nums">{count}</span>}
        </h2>
        {/* nothing to show yet: no "Alle anzeigen" into an empty list */}
        {count > 5 && (
          <Link href={href} className="inline-flex min-h-8 items-center gap-1 text-sm font-medium underline underline-offset-4" aria-label={`${t("all")}: ${title}`}>
            {t("all")}
            <ArrowRight aria-hidden className="size-3.5" />
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

function Rows({ children }: { children: ReactNode }) {
  return <ul className="divide-y divide-foreground/10">{children}</ul>;
}

function Row({ href, title, meta }: { href: string; title: string; meta: (string | null)[] }) {
  return (
    <li>
      <Link href={href} className="group flex items-center gap-3 py-3">
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium group-hover:underline group-hover:underline-offset-4">{title}</span>
          <span className="block truncate text-[0.8125rem] text-muted">{meta.filter(Boolean).join(" · ")}</span>
        </span>
        <ArrowRight aria-hidden className="size-4 shrink-0 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
      </Link>
    </li>
  );
}

function Empty({ children, href, action }: { children: ReactNode; href: string; action: string }) {
  return (
    <p className="max-w-prose text-sm text-muted">
      {children}{" "}
      <Link href={href} className="font-medium text-foreground underline underline-offset-4">
        {action}
      </Link>
    </p>
  );
}

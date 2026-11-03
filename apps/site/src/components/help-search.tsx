"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Locale } from "@/lib/i18n";
import { searchHelp } from "@/lib/search";
import type { Messages } from "@/messages/de";
import type { HelpEntry } from "../../content/help";

const GROUPS: HelpEntry["group"][] = ["start", "video", "team", "work", "account"];

export function HelpSearch({ entries, locale, t }: { entries: HelpEntry[]; locale: Locale; t: Messages["help"] }) {
  const [query, setQuery] = useState("");
  const hits = useMemo(() => searchHelp(entries, locale, query), [entries, locale, query]);
  const card = (e: HelpEntry) => (
    <li key={e.slug}>
      <Link href={`/${locale}/hilfe/${e.slug}/`} className="block rounded-lg border border-border p-4 hover:border-accent">
        <span className="font-semibold">{e.title[locale]}</span>
        <span className="mt-1 block text-sm text-muted">{e.summary[locale]}</span>
      </Link>
    </li>
  );
  return (
    <div className="mt-6">
      <label className="block max-w-xl">
        <span className="sr-only">{t.search}</span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t.search}
          className="w-full rounded-md border border-border bg-background px-3 py-2.5"
        />
      </label>
      {query.trim() ? (
        hits.length ? (
          <ul className="mt-6 grid gap-3 sm:grid-cols-2" aria-live="polite">{hits.map(card)}</ul>
        ) : (
          <p className="mt-6 text-muted" aria-live="polite">{t.noResults}</p>
        )
      ) : (
        GROUPS.map((g) => (
          <section key={g} className="mt-8">
            <h2 className="text-lg font-semibold">{t.groups[g]}</h2>
            <ul className="mt-3 grid gap-3 sm:grid-cols-2">{entries.filter((e) => e.group === g).map(card)}</ul>
          </section>
        ))
      )}
    </div>
  );
}

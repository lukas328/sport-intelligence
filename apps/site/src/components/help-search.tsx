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
  const row = (e: HelpEntry) => (
    <li key={e.slug} className="border-b border-rule">
      <Link href={`/${locale}/hilfe/${e.slug}/`} className="group block py-4">
        <span className="text-[1.1875rem] font-bold underline decoration-2 underline-offset-4 group-hover:decoration-[3px]">{e.title[locale]}</span>
        <span className="mt-1 block text-[1.0625rem] text-ink-2">{e.summary[locale]}</span>
      </Link>
    </li>
  );
  return (
    <div className="mt-6">
      <label className="block max-w-[36rem]">
        <span className="mb-2 block font-semibold">{t.search}</span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="min-h-14 w-full border-2 border-ink bg-paper px-4 text-[1.1875rem]"
        />
      </label>
      {query.trim() ? (
        hits.length ? (
          <ul className="mt-6 grid gap-x-10 md:grid-cols-2" aria-live="polite">
            {hits.map(row)}
          </ul>
        ) : (
          <p className="mt-6" aria-live="polite">
            {t.noResults}
          </p>
        )
      ) : (
        <div className="grid gap-x-10 md:grid-cols-2">
          {GROUPS.map((g) => {
            const list = entries.filter((e) => e.group === g);
            if (!list.length) return null;
            return (
              <section key={g} className="mt-10">
                <h3 className="font-slant text-[1.5rem]">{t.groups[g]}</h3>
                <ul className="mt-2 border-t-2 border-ink">{list.map(row)}</ul>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

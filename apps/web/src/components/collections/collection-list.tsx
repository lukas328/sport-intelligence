"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";

type Summary = Schemas["CollectionSummary"];

/** Every collection of the team, older playlists, presentations and tasks included (SPEC 7.7). */
export function CollectionList({ orgId, items, heading = true }: { orgId: string; items: Summary[]; heading?: boolean }) {
  const t = useTranslations("collections");
  const format = useFormatter();
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="all-collections" className="space-y-3" data-testid="collection-list">
      {heading && (
        <h2 id="all-collections" className="font-slant border-b-2 border-ink pb-2.5 text-[22px] md:text-[26px]">
          {t("all")}
        </h2>
      )}
      <ul className="m-0 list-none p-0">
        {items.map((c) => (
          <li key={c.id}>
            <Link href={`/app/${orgId}/collections/${c.id}`} className="group block border-t border-rule py-3.5 text-ink no-underline">
              <span className="font-slant block text-xl leading-tight group-hover:underline group-hover:underline-offset-4 md:text-[22px]">{c.title}</span>
              <span className="block text-[15px] text-ink-2">
                {[t("entries", { n: c.entries }), c.draft ? t("draft") : null, c.source !== "collection" ? t(`source_${c.source}`) : null, format.dateTime(new Date(c.created_at), { day: "numeric", month: "short" })]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";

type Summary = Schemas["CollectionSummary"];

/** Every collection of the team, older playlists, presentations and tasks included (SPEC 7.7). */
export function CollectionList({ orgId, items }: { orgId: string; items: Summary[] }) {
  const t = useTranslations("collections");
  const format = useFormatter();
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="all-collections" className="space-y-3" data-testid="collection-list">
      <h2 id="all-collections" className="border-b border-foreground/15 pb-3 text-lg font-bold">
        {t("all")}
      </h2>
      <ul className="divide-y divide-foreground/10">
        {items.map((c) => (
          <li key={c.id}>
            <Link href={`/app/${orgId}/collections/${c.id}`} className="group block py-3">
              <span className="block font-medium group-hover:underline group-hover:underline-offset-4">{c.title}</span>
              <span className="block text-[0.8125rem] text-muted">
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

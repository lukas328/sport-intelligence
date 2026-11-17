"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

interface Player {
  id: string;
  first_name: string;
  last_name: string;
  jersey_number: number | null;
}

/**
 * A squad without a goalkeeper (often one taken over from handball.ch, which gives no positions):
 * one tap per keeper sets «TW» (review R37). The keeper's saves then count as saves, not as
 * shots of a court player, and the goalkeeper figures have their person.
 */
export function MarkKeepers({ orgId, teamId, players }: { orgId: string; teamId: string; players: Player[] }) {
  const t = useTranslations("teamPage");
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  async function mark(p: Player) {
    setBusy(p.id);
    setFailed(false);
    const r = await api.PATCH("/v1/orgs/{org_id}/teams/{team_id}/roster/{entry_id}", {
      params: { path: { org_id: orgId, team_id: teamId, entry_id: p.id } },
      body: { main_position: "TW" },
    });
    setBusy(null);
    if (!r.response.ok) return setFailed(true);
    router.refresh();
  }
  return (
    <section className="max-w-[70ch] space-y-3 border-l-4 border-attn pl-4 md:col-span-3" data-testid="mark-keepers" aria-labelledby="mark-keepers-title">
      <h2 id="mark-keepers-title" className="font-slant m-0 text-xl">
        {t("keepersTitle")}
      </h2>
      <p className="m-0 text-[15px]">{t("keepersText")}</p>
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        {players.map((p) => (
          <li key={p.id}>
            <button
              type="button"
              onClick={() => void mark(p)}
              disabled={busy != null}
              className={cn("inline-flex min-h-11 cursor-pointer items-center gap-2 border-2 border-ink px-3 text-[15px] font-semibold disabled:cursor-wait disabled:opacity-60", busy === p.id && "bg-ink text-ground")}
              aria-label={t("keepersMark", { name: `${p.first_name} ${p.last_name}` })}
            >
              {p.jersey_number != null && <span className="font-num text-[17px]">{p.jersey_number}</span>}
              {p.first_name} {p.last_name}
            </button>
          </li>
        ))}
      </ul>
      {failed && (
        <p role="alert" className="m-0 text-[15px] font-semibold">
          {t("keepersFailed")}
        </p>
      )}
    </section>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { api } from "@/lib/client";
import { useEscape } from "@/lib/use-escape";
import { cn } from "@/lib/utils";

interface Player {
  id: string;
  first_name: string;
  last_name: string;
  jersey_number: number | null;
  main_position?: string | null;
}

/**
 * Who plays in goal, one tap per keeper (review R37). A team has more than one keeper: every tap
 * marks or unmarks one, and the block stays open until «Fertig» (Lukas, 17.11.: it closed after
 * the first keeper). With keepers marked it folds into one line that opens it again. The keepers'
 * saves then count as saves, not as shots of a court player, and the goalkeeper figures have
 * their person.
 */
export function MarkKeepers({ orgId, teamId, players }: { orgId: string; teamId: string; players: Player[] }) {
  const t = useTranslations("teamPage");
  const router = useRouter();
  const keepers = players.filter((p) => p.main_position === "TW");
  const [open, setOpen] = useState(keepers.length === 0);
  const [busy, setBusy] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  // Escape folds it like «Fertig» once a keeper is marked (A15)
  const panel = useRef<HTMLElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  // folded: the focus on the line that opens it again, not lost on the page
  const fold = () => {
    setOpen(false);
    requestAnimationFrame(() => opener.current?.focus());
  };
  useEscape(open && keepers.length > 0, fold, panel);
  async function toggle(p: Player) {
    setBusy(p.id);
    setFailed(false);
    const r = await api.PATCH("/v1/orgs/{org_id}/teams/{team_id}/roster/{entry_id}", {
      params: { path: { org_id: orgId, team_id: teamId, entry_id: p.id } },
      body: { main_position: p.main_position === "TW" ? null : "TW" },
    });
    setBusy(null);
    if (!r.response.ok) return setFailed(true);
    router.refresh();
  }
  if (!open) {
    return (
      <p className="m-0 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[15px] md:col-span-3" data-testid="mark-keepers">
        <span>{t("keepersSome", { n: keepers.length })}</span>
        <button ref={opener} type="button" onClick={() => setOpen(true)} className="cursor-pointer font-semibold underline underline-offset-4" data-testid="keepers-open">
          {t("keepersChange")}
        </button>
      </p>
    );
  }
  return (
    <section ref={panel} className="max-w-[70ch] space-y-3 border-l-4 border-attn pl-4 md:col-span-3" data-testid="mark-keepers" aria-labelledby="mark-keepers-title">
      <h2 id="mark-keepers-title" className="font-slant m-0 text-xl">
        {t("keepersTitle")}
      </h2>
      <p className="m-0 text-[15px]">{keepers.length === 0 ? t("keepersText") : t("keepersMore")}</p>
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        {players.map((p) => {
          const on = p.main_position === "TW";
          return (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => void toggle(p)}
                disabled={busy != null}
                aria-pressed={on}
                className={cn(
                  "inline-flex min-h-11 cursor-pointer items-center gap-2 border-2 border-ink px-3 text-[15px] font-semibold disabled:cursor-wait disabled:opacity-60",
                  on && "bg-ink text-ground",
                )}
                aria-label={t("keepersMark", { name: `${p.first_name} ${p.last_name}` })}
                data-testid="keeper-toggle"
              >
                {p.jersey_number != null && <span className="font-num text-[17px]">{p.jersey_number}</span>}
                {p.first_name} {p.last_name}
              </button>
            </li>
          );
        })}
      </ul>
      {keepers.length > 0 && (
        <button type="button" onClick={fold} className="min-h-11 cursor-pointer border-2 border-ink bg-ink px-4 text-[15px] font-semibold text-ground" data-testid="keepers-done">
          {t("keepersDone")}
        </button>
      )}
      {failed && (
        <p role="alert" className="m-0 text-[15px] font-semibold">
          {t("keepersFailed")}
        </p>
      )}
    </section>
  );
}

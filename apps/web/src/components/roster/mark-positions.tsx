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

/** the court positions, in the order of the line-up from left to right, the pivot last */
export const COURT_POSITIONS = ["LA", "RL", "RM", "RR", "RA", "KM"] as const;
export type CourtPosition = (typeof COURT_POSITIONS)[number];

/** The players a position block lists: everyone but the keepers, the ones without a position first. */
export function positionOrder<P extends Player>(players: readonly P[]): P[] {
  return players.filter((p) => p.main_position !== "TW").sort((a, b) => Number(Boolean(a.main_position)) - Number(Boolean(b.main_position)) || (a.jersey_number ?? 100) - (b.jersey_number ?? 100));
}

/**
 * The court positions as quick to set as the keepers (finding A14, the keeper block as the
 * pattern): choose a position, then tap every player who plays it; a second tap takes the
 * position away again. Closed on arrival: one line says what is missing and opens it.
 */
export function MarkPositions({ orgId, teamId, players }: { orgId: string; teamId: string; players: Player[] }) {
  const t = useTranslations("teamPage");
  const tr = useTranslations("positions");
  const router = useRouter();
  const field = positionOrder(players);
  const missing = field.filter((p) => !p.main_position).length;
  // a mode of its own, never open on arrival (app review UX-09): one line says what is missing
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<CourtPosition>("LA");
  const [busy, setBusy] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const panel = useRef<HTMLElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const fold = () => {
    setOpen(false);
    requestAnimationFrame(() => opener.current?.focus());
  };
  useEscape(open, fold, panel);
  if (field.length === 0) return null;
  async function toggle(p: Player) {
    setBusy(p.id);
    setFailed(false);
    const r = await api.PATCH("/v1/orgs/{org_id}/teams/{team_id}/roster/{entry_id}", {
      params: { path: { org_id: orgId, team_id: teamId, entry_id: p.id } },
      body: { main_position: p.main_position === pos ? null : pos },
    });
    setBusy(null);
    if (!r.response.ok) return setFailed(true);
    router.refresh();
  }
  if (!open) {
    return (
      <p className="m-0 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[15px] md:col-span-full" data-testid="mark-positions">
        <span>{missing > 0 ? t("positionsMissing", { n: missing }) : t("positionsAll")}</span>
        <button ref={opener} type="button" onClick={() => setOpen(true)} className="cursor-pointer font-semibold underline underline-offset-4" data-testid="positions-open">
          {missing > 0 ? t("positionsSet") : t("positionsChange")}
        </button>
      </p>
    );
  }
  return (
    <section ref={panel} className="max-w-[70ch] space-y-3 border-l-4 border-attn pl-4 md:col-span-full" data-testid="mark-positions" aria-labelledby="mark-positions-title">
      <h2 id="mark-positions-title" className="font-slant m-0 text-xl">
        {t("positionsTitle")}
      </h2>
      <p className="m-0 text-[15px]">{t("positionsText")}</p>
      {/* first the position, then the players who play it */}
      <div role="group" aria-label={t("positionsPick")} className="flex flex-wrap gap-2">
        {COURT_POSITIONS.map((k) => (
          <button
            key={k}
            type="button"
            aria-pressed={pos === k}
            onClick={() => setPos(k)}
            title={tr(k)}
            className={cn("inline-flex min-h-11 min-w-11 cursor-pointer items-center justify-center border-2 border-ink px-3 text-[15px] font-bold", pos === k ? "bg-ink text-ground" : "bg-transparent text-ink")}
            data-testid="position-pick"
          >
            <abbr title={tr(k)} className="no-underline">
              {k}
            </abbr>
          </button>
        ))}
      </div>
      <p className="m-0 text-[15px] font-semibold" aria-live="polite">
        {t("positionsTap", { position: tr(pos) })}
      </p>
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        {field.map((p) => {
          const on = p.main_position === pos;
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
                aria-label={t("positionsMark", { name: `${p.first_name} ${p.last_name}`, position: tr(pos) })}
                data-testid="position-toggle"
              >
                {p.jersey_number != null && <span className="font-num text-[17px]">{p.jersey_number}</span>}
                {p.first_name} {p.last_name}
                {/* the position the player has now, if it is another one */}
                {p.main_position && !on && <span className="text-[15px] font-bold text-ink-2">{p.main_position}</span>}
              </button>
            </li>
          );
        })}
      </ul>
      <button type="button" onClick={fold} className="min-h-11 cursor-pointer border-2 border-ink bg-ink px-4 text-[15px] font-semibold text-ground" data-testid="positions-done">
        {t("keepersDone")}
      </button>
      {failed && (
        <p role="alert" className="m-0 text-[15px] font-semibold">
          {t("positionsFailed")}
        </p>
      )}
    </section>
  );
}

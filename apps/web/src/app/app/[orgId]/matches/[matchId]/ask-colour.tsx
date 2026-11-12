"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { api } from "@/lib/client";
import { ASK_SHIRTS } from "@/lib/color";


/**
 * «Welche Farbe trägt Thalwil?» in the Wurf head (SPEC 7.13, Gegnerfarbe unbekannt): five shirts,
 * one tap saves the colour for this match and the next one against the opponent. Never guessed.
 */
export function AskColour({ orgId, matchId, opponent }: { orgId: string; matchId: string; opponent: string }) {
  const t = useTranslations("anlauf");
  const qc = useQueryClient();
  const [saved, setSaved] = useState(false);
  async function pick(colour: string) {
    const r = await api.PATCH("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: matchId } }, body: { opponent_kit: colour } });
    if (r.response.ok) {
      setSaved(true);
      void qc.invalidateQueries({ queryKey: ["match", matchId] });
    }
  }
  if (saved) return <p className="mt-2.5 text-sm font-bold">{t("colourSaved")}</p>;
  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-sm font-bold" data-testid="ask-colour">
      <span>{t("askColour", { opponent })}</span>
      {Object.entries(ASK_SHIRTS).map(([name, c]) => (
        <button key={c} type="button" onClick={() => void pick(c)} aria-label={t(`shirt.${name}` as "shirt.red")} className="grid size-11 cursor-pointer place-items-center bg-transparent">
          <i aria-hidden className="block size-7 border-[1.5px] border-club-ink" style={{ background: c }} />
        </button>
      ))}
    </div>
  );
}

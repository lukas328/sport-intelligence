"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";
import { api } from "@/lib/client";
import { SHIRTS } from "@/lib/color";

/**
 * «Welche Farbe trägt Farnwil?» in the Wurf head (SPEC 7.13, Gegnerfarbe unbekannt): the eight
 * shirts of the club and shirt choice (finding A17: it offered five),
 * one tap saves the colour for this match and the next one against the opponent. Never guessed.
 */
export function AskColour({ orgId, matchId, opponent }: { orgId: string; matchId: string; opponent: string }) {
  const t = useTranslations("anlauf");
  const qc = useQueryClient();
  const [saved, setSaved] = useState(false);
  const question = useId();
  // the colour buttons go once one is picked: the confirmation takes the focus, so it is read and
  // the focus does not fall back to the top of the page (audit)
  const done = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (saved) done.current?.focus();
  }, [saved]);
  async function pick(colour: string) {
    const r = await api.PATCH("/v1/orgs/{org_id}/matches/{match_id}", { params: { path: { org_id: orgId, match_id: matchId } }, body: { opponent_kit: colour } });
    if (r.response.ok) {
      setSaved(true);
      void qc.invalidateQueries({ queryKey: ["match", matchId] });
    }
  }
  if (saved)
    return (
      <p ref={done} tabIndex={-1} role="status" className="mt-2.5 text-sm font-bold outline-none" data-testid="ask-colour-saved">
        {t("colourSaved")}
      </p>
    );
  return (
    // the question on its line, the colours together in one row under it (review R16: they broke
    // apart next to a long opponent name)
    <div className="mt-2.5 text-sm font-bold" data-testid="ask-colour">
      <p id={question} className="m-0">
        {t("askColour", { opponent })}
      </p>
      <div className="-ml-2 flex flex-wrap" role="group" aria-labelledby={question}>
        {SHIRTS.map(([name, c]) => (
          <button key={c} type="button" onClick={() => void pick(c)} aria-label={t(`shirt.${name}` as "shirt.red")} className="grid size-11 shrink-0 cursor-pointer place-items-center bg-transparent">
            <i aria-hidden className="block size-7 border-[1.5px] border-club-ink" style={{ background: c }} />
          </button>
        ))}
      </div>
    </div>
  );
}

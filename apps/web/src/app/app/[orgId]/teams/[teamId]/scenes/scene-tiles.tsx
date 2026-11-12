"use client";

import type { Schemas } from "@handball/api-client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { CSSProperties } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { Bundle } from "@/components/anlauf/bundle";
import { clockOf } from "@/components/anlauf/three-things-view";
import { useShell } from "@/components/shell/context";
import { matchStyle } from "@/lib/color";
import { goalRuns, useMatchGraphics } from "@/lib/graphics";

type Match = Schemas["MatchSummary"];

/** Scene tiles (SPEC 7.6): the goals of the last matches with video, each as its own run. */
export function SceneTiles({ orgId, matches }: { orgId: string; matches: Match[] }) {
  const t = useTranslations("anlauf");
  return (
    <section aria-labelledby="goal-tiles" className="space-y-4">
      <SectionHead title={<span id="goal-tiles">{t("goalTiles")}</span>} />
      {matches.map((m) => (
        <MatchTiles key={m.id} orgId={orgId} m={m} />
      ))}
    </section>
  );
}

function MatchTiles({ orgId, m }: { orgId: string; m: Match }) {
  const t = useTranslations("anlauf");
  const { org } = useShell();
  const g = useMatchGraphics(orgId, m.id);
  const goals = g.data ? goalRuns(g.data).slice(-8).reverse() : [];
  if (goals.length === 0) return null;
  return (
    <div style={matchStyle([org.primary_color, org.secondary_color ?? null], m.opponent_color ? [m.opponent_color] : null) as CSSProperties}>
      <h3 className="font-slant mb-3 text-lg">{m.opponent_name}</h3>
      <ul className="m-0 grid list-none grid-cols-2 gap-x-3.5 gap-y-[18px] p-0 md:grid-cols-4 md:gap-x-5 md:gap-y-6">
        {goals.map((x) => {
          const label = t("goalOf", { team: x.team === "opp" ? m.opponent_name : t("us"), clock: clockOf(x.minute) });
          return (
            <li key={x.eventId}>
              <Link href={`/app/${orgId}/matches/${m.id}?tab=video`} className="flex flex-col gap-1.5 text-ink no-underline">
                <Bundle goals={[x]} width={200} label={label} />
                <b className="font-slant text-[17px] md:text-xl">{label}</b>
                {x.zone && <span className="text-[13px] leading-snug text-ink-2 md:text-[15px]">{t(`zoneShort.${x.zone}` as "zoneShort.la")}</span>}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

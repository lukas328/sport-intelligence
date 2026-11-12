"use client";

import type { Schemas } from "@handball/api-client";
import { useFormatter, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { AttnTag } from "@/components/anlauf/blocks";
import { Strip, WurfHead } from "@/components/anlauf/heads";
import { reportGoals, type MatchGraphics } from "@/lib/graphics";

type Match = Schemas["MatchOut"];

/**
 * The head of a match: the Wurf head on the tab Spiel, the Streifen on Video and Zahlen (one
 * head per screen, SPEC section 12). The result for screen readers in words.
 */
export function MatchHead({ match, ownName, oppName, view, graphics, children }: { match: Match; ownName: string; oppName: string; view: "game" | "video" | "numbers"; graphics: MatchGraphics | null | undefined; children?: ReactNode }) {
  const t = useTranslations("anlauf");
  const ta = t;
  const tm = useTranslations("matches");
  const format = useFormatter();
  const kickoff = new Date(match.kickoff_at);
  const title = match.opponent ? `${match.is_home ? ownName : oppName} ${tm("vs")} ${match.is_home ? oppName : ownName}` : `${tm("training")}: ${ownName}`;
  const when = format.dateTime(kickoff, { weekday: "long", day: "numeric", month: "long" });
  const half = match.halftime_own != null && match.halftime_opponent != null ? `${tm("halftime")} ${match.halftime_own}:${match.halftime_opponent}` : null;
  const kick = [when, match.competition, match.venue].filter(Boolean).join(" · ");
  const scoreText = match.score_own != null && match.score_opponent != null ? t("scoreLabel", { own: match.score_own, opp: match.score_opponent }) : null;
  const colourOpen = !match.opponent_colors && match.opponent ? <AttnTag className="ml-2">{t("colourOpen")}</AttnTag> : null;
  return (
    <div className="bleed-x -mt-6 lg:-mt-8">
      {scoreText && (
        <span className="sr-only" data-testid="score">
          {`${match.score_own}:${match.score_opponent}`}
        </span>
      )}
      {view === "game" ? (
        <WurfHead
          kick={kick}
          title={title}
          own={match.score_own}
          opp={match.score_opponent}
          ownName={ownName}
          oppName={oppName}
          goals={graphics ? reportGoals(graphics) : null}
          flightLabels={{ half: t("halftime", { v: "{v}" }), end: t("end", { v: "{v}" }), halfLevel: t("halftimeLevel"), endLevel: t("endLevel") }}
          meta={
            <>
              {half}
              {colourOpen}
            </>
          }
        >
          {children}
        </WurfHead>
      ) : (
        <Strip
          name={
            <h1 className="m-0 text-[length:inherit] leading-[inherit]">
              {ownName}
              {match.opponent && <span className="sr-only">{` ${ta("vsShort")} ${oppName}`}</span>}
            </h1>
          }
          sub={[match.opponent ? `${ta("vsShort")} ${oppName}` : null, when, match.venue].filter(Boolean).join(" · ")}
          own={match.score_own}
          opp={match.score_opponent}
        />
      )}
    </div>
  );
}

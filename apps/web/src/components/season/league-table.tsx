"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { OwnRowMark } from "@/components/anlauf/blocks";
import { signed, tableExcerpt, type TableRow } from "@/lib/league-table";
import { cn } from "@/lib/utils";

/**
 * The league table from handball.ch (livegang K1): an excerpt around the own team first, the
 * whole table inline with «Ganze Tabelle». The own team is marked (club band, bold, «dein Team»
 * for screen readers), a marked opponent in bold. Five columns fit a phone at 390 px: long team
 * names wrap.
 */
export function LeagueTable({ rows, caption, excerpt = 5, testid = "league-table", size = "md" }: { rows: TableRow[]; caption?: string; excerpt?: number; testid?: string; size?: "sm" | "md" }) {
  const t = useTranslations("leagueTable");
  const [all, setAll] = useState(false);
  const tableId = useId();
  const short = tableExcerpt(rows, excerpt);
  const shown = all ? rows : short;
  const more = short.length < rows.length;
  if (rows.length === 0) return null;
  return (
    <div>
      <table id={tableId} className={cn("w-full border-collapse", size === "sm" ? "text-[15px]" : "text-[17px]")} data-testid={testid} data-all={all || !more ? "true" : "false"}>
        {caption && <caption className="mb-1 text-left text-[15px] font-semibold text-ink-2">{caption}</caption>}
        <thead>
          <tr className="border-b-2 border-ink text-[15px] text-ink-2">
            <th scope="col" className="w-9 py-1.5 text-left font-semibold">
              <abbr title={t("rank")} className="no-underline">{t("rankShort")}</abbr>
            </th>
            <th scope="col" className="py-1.5 text-left font-semibold">{t("team")}</th>
            <th scope="col" className="w-10 py-1.5 text-right font-semibold">
              <abbr title={t("games")} className="no-underline">{t("gamesShort")}</abbr>
            </th>
            <th scope="col" className="w-12 py-1.5 text-right font-semibold">
              <abbr title={t("diff")} className="no-underline">{t("diffShort")}</abbr>
            </th>
            <th scope="col" className="w-11 py-1.5 text-right font-semibold">
              <abbr title={t("points")} className="no-underline">{t("pointsShort")}</abbr>
            </th>
          </tr>
        </thead>
        <tbody>
          {shown.map((r, i) => {
            // a gap in the excerpt (own team and opponent far apart): a firmer line
            const prev = shown[i - 1];
            const gap = !all && prev?.rank != null && r.rank != null && r.rank - prev.rank > 1;
            return (
              <tr key={r.key} className={cn(r.own ? "border-y-2 border-ink font-bold" : gap ? "border-t-2 border-dashed border-rule" : "border-t border-rule", r.marked && "font-bold")} aria-current={r.own ? "true" : undefined} data-own={r.own ? "" : undefined}>
                <td className="py-2 pr-2 tabular-nums">{r.rank}</td>
                <th scope="row" className={cn("py-2 text-left", r.own || r.marked ? "font-bold" : "font-normal")}>
                  {r.own && <OwnRowMark />}
                  {r.name}
                  {r.own && <span className="sr-only"> ({t("own")})</span>}
                </th>
                <td className="py-2 text-right tabular-nums">{r.games}</td>
                <td className="py-2 text-right tabular-nums">{signed(r.diff)}</td>
                <td className="py-2 text-right tabular-nums">{r.points}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {more && (
        <button
          type="button"
          onClick={() => setAll((v) => !v)}
          aria-expanded={all}
          aria-controls={tableId}
          className="mt-2 inline-flex min-h-11 cursor-pointer items-center border-0 bg-transparent p-0 text-[15px] font-bold text-ink underline decoration-[1.5px] underline-offset-4"
          data-testid={`${testid}-toggle`}
        >
          {all ? t("showLess") : t("showAll", { n: rows.length })}
        </button>
      )}
    </div>
  );
}

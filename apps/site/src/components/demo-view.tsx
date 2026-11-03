"use client";

import { useMemo, useState } from "react";
import { Court } from "@/components/court";
import { demoFigures, filterShots, type DemoMatch, type DemoShot } from "@/lib/demo";
import { fmt, type Locale } from "@/lib/i18n";
import type { Messages } from "@/messages/de";

const COLOURS: Record<string, string> = { goal: "#15803d", save: "#b91c1c", miss: "#64748b", post: "#ca8a04", blocked: "#7c3aed" };

/** Read-only demo of a match analysis (addendum 01, 4.13): fictional events, real metrics code. */
export function DemoView({ match, t, locale }: { match: DemoMatch; t: Messages["demo"]; locale: Locale }) {
  const [side, setSide] = useState<"own" | "opponent" | "both">("own");
  const [outcome, setOutcome] = useState<string>("all");
  const [period, setPeriod] = useState<number>(0);
  const [selected, setSelected] = useState<DemoShot | null>(null);
  const shots = useMemo(() => filterShots(match, { side, outcome, period }), [match, side, outcome, period]);
  const pct = (v: number | null) => (v === null ? "-" : `${Math.round(v * 100)} %`);
  const nf = new Intl.NumberFormat(locale === "de" ? "de-CH" : locale, { maximumFractionDigits: 1 });
  const select = "rounded-md border border-border bg-background px-2 py-1.5 text-sm";
  const teamName = (s: string) => (s === "own" ? match.own : match.opponent);
  const final = match.stats.timeline.final;

  return (
    <div className="space-y-8">
      <p className="text-2xl font-bold" aria-label={`${match.own} ${final.own}, ${match.opponent} ${final.opp}`}>
        {match.own} {final.own} : {final.opp} {match.opponent}
      </p>
      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm">
          {t.team}
          <select className={select} value={side} onChange={(e) => setSide(e.target.value as typeof side)}>
            <option value="own">{match.own}</option>
            <option value="opponent">{match.opponent}</option>
            <option value="both">{t.both}</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          {t.outcome}
          <select className={select} value={outcome} onChange={(e) => setOutcome(e.target.value)}>
            <option value="all">{t.all}</option>
            {Object.entries(t.outcomes).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          {t.half}
          <select className={select} value={period} onChange={(e) => setPeriod(Number(e.target.value))}>
            <option value={0}>{t.all}</option>
            <option value={1}>{fmt(t.halfN, { n: 1 })}</option>
            <option value={2}>{fmt(t.halfN, { n: 2 })}</option>
          </select>
        </label>
      </div>

      <section aria-labelledby="shotmap">
        <h2 id="shotmap" className="text-xl font-semibold">
          {t.shotMap} <span className="text-base font-normal text-muted">({fmt(t.shots, { count: shots.length })})</span>
        </h2>
        <div className="mt-3 max-w-3xl">
          <Court label={t.shotMapLabel}>
            {shots.map((s) => (
              <circle
                key={s.id}
                cx={s.x}
                cy={s.y}
                r={selected?.id === s.id ? 0.75 : 0.5}
                fill={COLOURS[s.outcome] ?? "#64748b"}
                stroke={selected?.id === s.id ? "var(--foreground)" : "white"}
                strokeWidth={0.12}
                tabIndex={0}
                role="button"
                aria-label={describe(s)}
                className="cursor-pointer outline-none focus-visible:stroke-[var(--foreground)] focus-visible:[stroke-width:0.25]"
                onClick={() => setSelected(s)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setSelected(s)}
              />
            ))}
          </Court>
        </div>
        <ul className="mt-2 flex flex-wrap gap-3 text-xs text-muted" aria-hidden="true">
          {Object.entries(t.outcomes).map(([k, v]) => (
            <li key={k} className="flex items-center gap-1">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: COLOURS[k] }} /> {v}
            </li>
          ))}
        </ul>
        <p className="mt-3 min-h-6 text-sm" aria-live="polite">
          {selected ? `${side === "both" ? `${teamName(selected.side)}, ` : ""}${describe(selected)}` : t.selectHint}
        </p>
      </section>

      <section aria-labelledby="figures">
        <h2 id="figures" className="text-xl font-semibold">{t.stats}</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full max-w-2xl text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2" />
                <th className="py-2">{match.own}</th>
                <th className="py-2">{match.opponent}</th>
              </tr>
            </thead>
            <tbody>
              {demoFigures(match).map(([key, own, opp]) => (
                <tr key={key} className="border-b border-border">
                  <th scope="row" className="py-2 text-left font-normal">{t[key]}</th>
                  <td className="py-2">{key === "shootingPct" ? pct(own) : nf.format(own ?? 0)}</td>
                  <td className="py-2">{key === "shootingPct" ? pct(opp) : nf.format(opp ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-sm text-muted">{t.xgHint}</p>
      </section>

      <section aria-labelledby="timeline">
        <h2 id="timeline" className="text-xl font-semibold">{t.timeline}</h2>
        <Timeline match={match} label={t.timelineLabel} />
      </section>
    </div>
  );

  function describe(s: DemoShot): string {
    return fmt(t.selected, {
      number: s.number ?? "-",
      minute: Math.floor(s.clock_s / 60) + 1,
      type: t.shotTypes[s.shot_type as keyof typeof t.shotTypes] ?? s.shot_type,
      outcome: t.outcomes[s.outcome as keyof typeof t.outcomes] ?? s.outcome,
      xg: nf.format(s.xg),
    });
  }
}

function Timeline({ match, label }: { match: DemoMatch; label: string }) {
  const { score, final } = match.stats.timeline;
  const pts = [...score, { clock_s: 3600, own: final.own, opp: final.opp }];
  const max = Math.max(...pts.map((p) => Math.max(p.own, p.opp)), 1);
  const path = (k: "own" | "opp") =>
    pts.map((p, i) => `${i ? "L" : "M"}${(p.clock_s / 3600) * 600},${120 - (p[k] / max) * 110}`).join(" ");
  return (
    <svg viewBox="0 0 600 125" role="img" aria-label={label} className="mt-3 h-auto w-full max-w-3xl">
      <line x1={300} x2={300} y1={0} y2={120} stroke="var(--border)" strokeDasharray="4 3" />
      <line x1={0} x2={600} y1={120} y2={120} stroke="var(--border)" />
      <path d={path("own")} fill="none" stroke="var(--accent)" strokeWidth={2.5} />
      <path d={path("opp")} fill="none" stroke="var(--muted)" strokeWidth={2} />
      <text x={4} y={12} fontSize={11} fill="var(--accent)">{match.own}</text>
      <text x={4} y={26} fontSize={11} fill="var(--muted)">{match.opponent}</text>
    </svg>
  );
}

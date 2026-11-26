"use client";

import { FOCI, filterDrills, type Focus, type Level } from "@handball/tactics";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { asLang, DrillCard } from "@/components/training/drill-card";
import { cn } from "@/lib/utils";
import { ClubDrills } from "./club-drills";

const MINUTES = [10, 12, 15] as const;

/**
 * The drill library (K21): the club's own drills, then the library, filtered by focus, level,
 * duration and name. A link from a training tip (?focus=wings) opens with that focus; a link to
 * one drill (#id) opens its description.
 */
export function DrillLibrary({ orgId, initialFocus }: { orgId: string; initialFocus: Focus[] }) {
  const t = useTranslations("drills");
  const lang = asLang(useLocale());
  const [focus, setFocus] = useState<Focus[]>(initialFocus);
  const [level, setLevel] = useState<Level | "">("");
  const [minutes, setMinutes] = useState<number | "">("");
  const [query, setQuery] = useState("");
  const [hash, setHash] = useState<string | null>(null);
  useEffect(() => {
    const read = () => setHash(window.location.hash.slice(1) || null);
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, []);

  const list = useMemo(() => {
    const base = filterDrills({ level: level || null, minutes: minutes || null, query, lang });
    return focus.length ? base.filter((d) => d.focus.some((f) => focus.includes(f))) : base;
  }, [focus, level, minutes, query, lang]);
  const filtered = focus.length > 0 || level !== "" || minutes !== "" || query.trim() !== "";
  const chip = (on: boolean) => cn("-mb-px min-h-11 min-w-11 shrink-0 whitespace-nowrap border-b-2 px-0.5 text-[15px] font-semibold", on ? "border-foreground text-foreground" : "border-transparent text-muted hover:text-foreground");
  const control = "min-h-11 bg-raised px-2 text-base ring-1 ring-inset ring-border";

  return (
    <div className="space-y-6">
      {/* one scrolling row of focus filters (twelve pills filled the first phone screen) */}
      <div role="group" aria-label={t("focusLabel")} className="scrollbar-none -mx-1 flex gap-x-4 overflow-x-auto border-b border-foreground/15 px-1 sm:flex-wrap">
        <button type="button" aria-pressed={focus.length === 0} onClick={() => setFocus([])} className={chip(focus.length === 0)}>
          {t("all")}
        </button>
        {FOCI.map((f) => (
          <button key={f} type="button" aria-pressed={focus.length === 1 && focus[0] === f} onClick={() => setFocus([f])} className={chip(focus.length === 1 && focus[0] === f)}>
            {t(`focus_${f}`)}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">{t("levelLabel")}</span>
          <select value={level} onChange={(e) => setLevel(e.target.value as Level | "")} className={control}>
            <option value="">{t("anyLevel")}</option>
            <option value="basic">{t("level_basic")}</option>
            <option value="advanced">{t("level_advanced")}</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">{t("duration")}</span>
          <select value={minutes} onChange={(e) => setMinutes(e.target.value ? Number(e.target.value) : "")} className={control}>
            <option value="">{t("anyMinutes")}</option>
            {MINUTES.map((m) => (
              <option key={m} value={m}>
                {t("upTo", { minutes: m })}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-0 basis-full flex-col gap-1 text-sm sm:max-w-xs sm:flex-1 sm:basis-auto">
          <span className="font-medium">{t("search")}</span>
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("searchPlaceholder")} className={control} />
        </label>
      </div>

      <ClubDrills orgId={orgId} focus={focus} />

      <section className="space-y-3" aria-labelledby="library-title">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="library-title" className="text-xl">
            {focus.length === 1 ? t("suggestedFor", { focus: t(`focus_${focus[0]!}`) }) : t("library")}
          </h2>
          <p className="text-[15px] text-muted" aria-live="polite">
            {t("count", { n: list.length })}
          </p>
        </div>
        {list.length === 0 ? (
          <p className="text-[15px]">
            {t("none")}{" "}
            {filtered && (
              <button type="button" className="font-semibold underline underline-offset-4" onClick={() => (setFocus([]), setLevel(""), setMinutes(""), setQuery(""))}>
                {t("reset")}
              </button>
            )}
          </p>
        ) : (
          <ul className="grid border-t-2 border-foreground md:grid-cols-2 md:gap-x-12" data-testid="drills">
            {list.map((d) => (
              <li key={d.id} className="border-b border-foreground/15 py-5">
                <DrillCard drill={d} lang={lang} open={hash === d.id} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

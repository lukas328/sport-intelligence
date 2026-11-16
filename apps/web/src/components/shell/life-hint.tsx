"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { sectionOf, type Section } from "@/lib/nav-model";
import { useShell } from "./context";

const AREAS: Section[] = ["dates", "plan", "assignments", "myscenes", "consents", "overview"];
const KEY = (area: string) => `hb_life_hint_${area}`;

/**
 * The first visit of each area of Teamleben (finding K16): one short note what the area is for and
 * who sees what, closed with «Verstanden» and not shown again in this browser.
 */
export function LifeHint() {
  const t = useTranslations("teamLife");
  const path = usePathname();
  const { mode } = useShell();
  const area = sectionOf(path);
  const known = area && AREAS.includes(area) ? area : null;
  const [seen, setSeen] = useState(true);
  useEffect(() => {
    if (!known) return;
    try {
      setSeen(window.localStorage.getItem(KEY(known)) === "1");
    } catch {
      setSeen(false);
    }
  }, [known]);
  if (!known || seen) return null;
  const who = mode === "staff" ? "staff" : mode === "family" ? "family" : "player";
  return (
    <aside className="mb-6 max-w-[70ch] border-l-4 border-attn bg-surface px-4 py-3" aria-label={t("hintLabel")} data-testid="life-hint">
      <p className="m-0 text-[15px] font-bold">{t(`hint_${known}_title`)}</p>
      <p className="mt-1 mb-2 text-[15px]">{t(`hint_${known}_${who}`)}</p>
      <button
        type="button"
        className="min-h-11 cursor-pointer text-[15px] font-bold underline decoration-[1.5px] underline-offset-4"
        onClick={() => {
          try {
            window.localStorage.setItem(KEY(known), "1");
          } catch {
            /* storage unavailable: hidden until the page reloads */
          }
          setSeen(true);
        }}
      >
        {t("hintOk")}
      </button>
    </aside>
  );
}

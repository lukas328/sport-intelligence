"use client";

import { type ReactNode, useEffect, useState } from "react";
import { PhoneFrame } from "@/components/phone-chat";
import { cn } from "@/lib/cn";
import { fmt } from "@/lib/i18n";
import type { Messages } from "@/messages/de";

export interface PlayerScene {
  clock: string;
  number: number | null;
}

/**
 * What a player sees when he opens the link (apps/web share page: «Sammlung · 4 Szenen», «Nur
 * ansehen, ohne Konto», the running order with «läuft» and «gesehen»): in the same neutral phone as
 * the team chat. The video is the website's blurred hall recording, nobody recognisable; the bar
 * runs as if the second scene plays (still with reduced motion).
 */
export function PlayerPhone({ t, scenes, clock }: { t: Messages["demo"]["player"]; scenes: PlayerScene[]; clock: string }) {
  const playing = 1;
  return (
    <PhoneFrame label={t.label} clock={clock}>
      <div className="flex flex-1 flex-col overflow-hidden bg-[#f7f6f2]">
        <p className="mx-3 mb-2 truncate rounded-[999px] bg-black/[.06] px-3 py-1 text-center text-[0.6875rem] text-[#5f6368]">app.handball-intelligence.com/s/q7Lm2xKd</p>
        <div className="px-3">
          <p className="text-[0.75rem] font-semibold tracking-wide text-[#5f6368] uppercase">{t.kick}</p>
          <p className="font-slant text-[1.375rem] leading-tight">{t.title}</p>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[0.75rem] text-[#5f6368]">
            <span>{t.team}</span>
            <span className="rounded-[4px] bg-[#d6ebdc] px-1.5 font-semibold text-[#0b4d36]">{t.viewOnly}</span>
          </p>
        </div>
        <div className="relative mx-3 mt-2.5 aspect-[16/9] overflow-hidden rounded-[0.5rem] bg-[#7d7f80]">
          <img src="/media/halle.webp" alt="" width={800} height={450} loading="lazy" decoding="async" className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-[linear-gradient(180deg,rgb(22_23_26/.05)_45%,rgb(22_23_26/.6))]" />
          <span className="absolute top-2 left-2 rounded-[4px] bg-black/60 px-1.5 py-0.5 text-[0.6875rem] font-semibold text-white">{fmt(t.video, { i: playing + 1, n: scenes.length })}</span>
          <div className="absolute inset-x-2 bottom-2 flex items-center gap-2 font-mono text-[0.6875rem] font-semibold text-white">
            <svg viewBox="0 0 20 20" className="size-3 shrink-0">
              <path d="M5 3h3v14H5zM12 3h3v14h-3z" fill="currentColor" />
            </svg>
            <span className="relative h-1 flex-1 bg-white/35">
              <i className="scene-progress absolute inset-y-0 left-0 w-full origin-left bg-white" />
            </span>
            <span>{scenes[playing]?.clock}</span>
          </div>
        </div>
        <p className="mx-3 mt-3 text-[0.75rem] font-semibold text-[#5f6368]">{t.run}</p>
        <ol className="mx-3 mt-1 border-t border-black/10">
          {scenes.map((s, i) => (
            <li key={s.clock} className={cn("flex items-center gap-2 border-b border-black/10 py-1.5 text-[0.8125rem]", i === playing && "font-bold")}>
              <span className="w-10 font-mono text-[0.75rem]">{s.clock}</span>
              <span className="min-w-0 flex-1 truncate">{s.number != null ? fmt(t.row, { number: s.number }) : s.clock}</span>
              <span className={cn("shrink-0 text-[0.6875rem]", i === playing ? "rounded-[4px] bg-[#ffd23c] px-1 text-[#16171a]" : "text-[#5f6368]")}>{i < playing ? t.seen : i === playing ? t.running : ""}</span>
            </li>
          ))}
        </ol>
        <div className="mx-3 mt-auto mb-6 grid gap-1.5 pt-2">
          <span className="grid min-h-9 place-items-center rounded-[0.5rem] bg-[#16171a] text-[0.8125rem] font-semibold text-white">{t.next}</span>
          <span className="text-center text-[0.6875rem] leading-snug text-[#5f6368]">{t.onlyLink}</span>
        </div>
      </div>
    </PhoneFrame>
  );
}

/**
 * Tuesday: the team chat and the player's view side by side; on a phone a switch shows one at a
 * time (without JavaScript both stand one under the other).
 */
export function Tuesday({ labels, chat, player }: { labels: string[]; chat: ReactNode; player: ReactNode }) {
  const [js, setJs] = useState(false);
  const [pick, setPick] = useState(0);
  useEffect(() => setJs(true), []);
  return (
    <div>
      {js && (
        <div role="group" className="mx-auto mb-6 grid max-w-[20.5rem] grid-cols-2 border-2 border-ink md:hidden">
          {labels.map((l, i) => (
            <button key={l} type="button" aria-pressed={i === pick} onClick={() => setPick(i)} className={cn("min-h-12 cursor-pointer px-2 text-[1.0625rem] font-bold", i === pick ? "bg-ink text-ground" : "bg-paper")}>
              {l}
            </button>
          ))}
        </div>
      )}
      <div className="grid grid-cols-1 gap-10 md:grid-cols-2 md:gap-6 lg:gap-10">
        {[chat, player].map((node, i) => (
          <figure key={i} className={cn("m-0 min-w-0", js && i !== pick && "max-md:hidden")}>
            {node}
            <figcaption className="mt-3 text-center text-base font-semibold text-ink-2 max-md:hidden">{labels[i]}</figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}

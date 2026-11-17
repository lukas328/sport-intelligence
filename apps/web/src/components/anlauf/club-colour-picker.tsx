"use client";

import { useTranslations } from "next-intl";
import { CLUB_COLOURS } from "@/lib/color";
import { cn } from "@/lib/utils";

/**
 * The club colours as one radio group of shirts (decision E8): one tap, what a coach knows without
 * a colour picker. Every colour carries white text at 4.5:1, because the app head writes white on
 * it. `value` null: nothing chosen yet, no shirt is marked. Used by the onboarding step «Eure
 * Vereinsfarbe», the confirmation of a team from the official data and the club page.
 */
export function ClubColourPicker({
  value,
  onChange,
  legend,
  name = "club-colour",
  note,
  id,
}: {
  value: string | null;
  onChange: (hex: string) => void;
  legend: string;
  name?: string;
  note?: string;
  id?: string;
}) {
  const t = useTranslations("onboarding");
  const current = value?.toLowerCase() ?? null;
  return (
    <fieldset className="min-w-0 scroll-mt-24 border-0 p-0" data-testid="club-colour-picker" id={id}>
      <legend className="font-slant mb-3 w-full border-b-2 border-ink pb-2.5 text-[22px] md:text-2xl">{legend}</legend>
      <div className="grid w-fit grid-cols-4 gap-3 sm:flex sm:flex-wrap">
        {CLUB_COLOURS.map(([key, hex]) => (
          <label
            key={key}
            title={t(`shirt.${key}`)}
            className={cn(
              "grid size-[52px] cursor-pointer place-items-center border-2 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ink has-[:focus-visible]:ring-offset-2",
              current === hex ? "border-ink" : "border-transparent hover:border-rule",
            )}
          >
            <input type="radio" name={name} value={hex} checked={current === hex} onChange={() => onChange(hex)} className="sr-only" aria-label={t(`shirt.${key}`)} />
            <svg aria-hidden viewBox="0 0 24 24" className="size-10">
              <path d="M8 3 4.2 4.8 2 9l3.2 1.6L6.4 9v12h11.2V9l1.2 1.6L22 9l-2.2-4.2L16 3c-.9 1.4-2.3 2.2-4 2.2S8.9 4.4 8 3Z" fill={hex} stroke="var(--ink)" strokeOpacity={0.35} strokeWidth="1" strokeLinejoin="round" />
              {/* the chosen shirt carries a tick: the choice does not hang on the frame alone */}
              {current === hex && <path d="m8.6 13.4 2.4 2.4 4.6-4.8" fill="none" stroke="var(--paper)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />}
            </svg>
          </label>
        ))}
      </div>
      {note && <p className="mt-3 mb-0 text-[15px] text-ink-2">{note}</p>}
    </fieldset>
  );
}

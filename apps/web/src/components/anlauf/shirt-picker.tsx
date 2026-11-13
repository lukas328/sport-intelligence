"use client";

import { useTranslations } from "next-intl";
import { SHIRTS } from "@/lib/color";
import { cn } from "@/lib/utils";

/**
 * The eight shirts of the onboarding (SPEC 7.12) as one radio group: what a coach knows without
 * a colour picker. Used by the onboarding by hand and the club page (UX test B27, B43).
 */
export function ShirtPicker({ value, onChange, legend, name = "shirt", note }: { value: string; onChange: (hex: string) => void; legend: string; name?: string; note?: string }) {
  const t = useTranslations("onboarding");
  return (
    <fieldset className="m-0 border-0 p-0" data-testid="shirt-picker">
      <legend className="font-slant mb-3 w-full border-b-2 border-ink pb-2.5 text-[22px] md:text-2xl">{legend}</legend>
      <div className="grid w-fit grid-cols-4 gap-3 sm:flex sm:flex-wrap">
        {SHIRTS.map(([key, hex]) => (
          <label key={key} className={cn("grid size-[52px] cursor-pointer place-items-center border-2 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ink", value.toLowerCase() === hex ? "border-ink" : "border-transparent")}>
            <input type="radio" name={name} value={hex} checked={value.toLowerCase() === hex} onChange={() => onChange(hex)} className="sr-only" aria-label={t(`shirt.${key}`)} />
            <svg aria-hidden viewBox="0 0 24 24" className="size-10">
              <path d="M8 3 4.2 4.8 2 9l3.2 1.6L6.4 9v12h11.2V9l1.2 1.6L22 9l-2.2-4.2L16 3c-.9 1.4-2.3 2.2-4 2.2S8.9 4.4 8 3Z" fill={hex} stroke="var(--ink)" strokeOpacity={0.35} strokeWidth="1" strokeLinejoin="round" />
            </svg>
          </label>
        ))}
      </div>
      {note && <p className="mt-3 text-[15px] text-ink-2">{note}</p>}
    </fieldset>
  );
}

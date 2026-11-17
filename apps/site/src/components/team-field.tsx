"use client";

import { FARBE, useShirt } from "@/components/kit";
import { START_ACTION, byHandUrl } from "@/lib/site";

/**
 * «Wie heisst dein Team?»: the main way in. One field, one button, the label above the field and
 * an example below. A plain GET form to the app's team preview (`/einstieg?q=`), no script, no
 * account; the app shows the team from the federation data and offers to save it. The federation
 * data covers teams in Switzerland only, so `after` says so and `manual` links straight to the way by
 * hand, without a search that finds nothing first.
 */
export function TeamField({
  id,
  label,
  button,
  example,
  after,
  manual,
  appLocale,
  onClub = false,
}: {
  id: string;
  label: string;
  button: string;
  example: string;
  /** what «Zeigen» brings, right under the field (S7) */
  after?: string;
  /** the link to the way by hand, right after `after` */
  manual?: string;
  appLocale: string;
  onClub?: boolean;
}) {
  const { shirt, chosen } = useShirt();
  return (
    <form action={START_ACTION} method="get" role="search" className="w-full max-w-[34rem]">
      <label htmlFor={id} className={`block text-[1.375rem] leading-tight font-bold md:text-[1.625rem] ${onClub ? "text-club-ink" : "text-ink"}`}>
        {label}
      </label>
      <div className="mt-3 flex flex-col gap-2 min-[480px]:flex-row">
        <input
          id={id}
          name="q"
          type="text"
          required
          minLength={3}
          autoComplete="organization"
          enterKeyHint="search"
          aria-describedby={`${id}-example`}
          className="min-h-16 w-full min-w-0 flex-1 border-2 border-ink bg-paper px-4 text-[1.25rem] text-ink shadow-[0_0_0_2px_var(--club-ink)] outline-offset-4"
        />
        {chosen && shirt && <input type="hidden" name="farbe" value={FARBE[shirt]} />}
        <input type="hidden" name="lang" value={appLocale} />
        <button type="submit" className="btn btn-ink min-h-16 px-8 text-[1.25rem] shadow-[0_0_0_2px_var(--club-ink)]">
          {button}
        </button>
      </div>
      <p id={`${id}-example`} className={`mt-2 text-[1.0625rem] ${onClub ? "text-club-ink" : "text-ink-2"}`}>
        {example}
      </p>
      {after && (
        <p className={`mt-2 max-w-[34rem] text-[1.0625rem] ${onClub ? "text-club-ink" : "text-ink-2"}`}>
          {after}
          {manual && (
            <>
              {" "}
              <a href={byHandUrl(appLocale, chosen && shirt ? FARBE[shirt] : undefined)} className={`font-bold underline decoration-2 underline-offset-4 ${onClub ? "text-club-ink" : "text-ink"}`}>
                {manual}
              </a>
            </>
          )}
        </p>
      )}
    </form>
  );
}

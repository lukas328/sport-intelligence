"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { CURRENCIES, currencyOf, DEFAULT_CURRENCY, type Currency } from "@/lib/currency";

/** the event the switch sends to every price on the page */
const EVENT = "hb-currency";

/** The visitor's currency (lib/currency.ts): `?cur=`, else from the browser's languages. */
export function useCurrency(): [Currency, (c: Currency) => void] {
  const [cur, setCur] = useState<Currency>(DEFAULT_CURRENCY);
  useEffect(() => {
    setCur(currencyOf(navigator.languages ?? [navigator.language], new URLSearchParams(window.location.search).get("cur")));
    const on = (e: Event) => setCur((e as CustomEvent<Currency>).detail);
    window.addEventListener(EVENT, on);
    return () => window.removeEventListener(EVENT, on);
  }, []);
  const set = (c: Currency) => {
    // only in the address, so a shared link keeps it; nothing in the browser's storage
    const url = new URL(window.location.href);
    url.searchParams.set("cur", c.toLowerCase());
    window.history.replaceState(null, "", url);
    window.dispatchEvent(new CustomEvent(EVENT, { detail: c }));
  };
  return [cur, set];
}

/** A text with `{cur}` in it, filled with the visitor's currency. */
export function Cur({ text }: { text: string }) {
  const [cur] = useCurrency();
  return <>{text.replaceAll("{cur}", cur)}</>;
}

/** Two buttons, CHF and EUR, on «Preise». */
export function CurrencySwitch({ label, className }: { label: string; className?: string }) {
  const [cur, set] = useCurrency();
  return (
    <div role="group" aria-label={label} className={cn("inline-flex items-center gap-3", className)}>
      <span className="text-[1.0625rem] font-semibold">{label}</span>
      <span className="inline-flex border-2 border-ink">
        {CURRENCIES.map((c) => (
          <button
            key={c}
            type="button"
            aria-pressed={cur === c}
            onClick={() => set(c)}
            className={cn("min-h-12 min-w-16 px-4 font-mono text-base font-semibold", cur === c ? "bg-ink text-paper" : "bg-paper text-ink")}
          >
            {c}
          </button>
        ))}
      </span>
    </div>
  );
}

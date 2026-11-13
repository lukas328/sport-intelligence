"use client";

import Link from "next/link";
import { createContext, type CSSProperties, type ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { kit, kitVars, SHIRTS } from "@/lib/color";
import { startUrl } from "@/lib/site";

/** The demo opponent: black with white (TV Muster). The clash rule decides how it shows. */
export const DEMO_OPPONENT = ["#17191c", "#ffffff"] as const;

export type ShirtKey = (typeof SHIRTS)[number][0];
const KEYS = SHIRTS.map(([k]) => k) as readonly ShirtKey[];

function isShirt(v: string | null): v is ShirtKey {
  return v !== null && (KEYS as readonly string[]).includes(v);
}

function second(hex: string): string {
  return hex === "#ffffff" || hex === "#f6c500" ? "#17191c" : "#ffffff";
}

export function kitStyle(key: ShirtKey): CSSProperties {
  const hex = SHIRTS.find(([k]) => k === key)![1];
  return kitVars(kit([hex, second(hex)], DEMO_OPPONENT)) as CSSProperties;
}

/** German names the app takes as `farbe=` on /einstieg (OPEN_QUESTIONS Q-SITE-9). */
export const FARBE: Record<ShirtKey, string> = { blue: "blau", red: "rot", yellow: "gelb", black: "schwarz", white: "weiss", green: "gruen", orange: "orange", purple: "violett" };

interface KitState {
  shirt: ShirtKey;
  /** true once the visitor picked a colour (or came with ?kit=): only then it goes to the app */
  chosen: boolean;
  setShirt: (k: ShirtKey) => void;
  inScope: boolean;
}
const Ctx = createContext<KitState>({ shirt: "blue", chosen: false, setShirt: () => {}, inScope: false });

/**
 * The visitor's colour for the demo match. Starts blue, or with `?kit=` from a link (the start
 * page hands the choice to the demo that way); nothing is stored in the browser.
 */
export function KitScope({ children, className }: { children: ReactNode; className?: string }) {
  const outer = useContext(Ctx);
  const [shirt, setShirtState] = useState<ShirtKey>("blue");
  const [chosen, setChosen] = useState(false);
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("kit");
    if (isShirt(q)) {
      setShirtState(q);
      setChosen(true);
    }
  }, []);
  const value = useMemo(() => ({ shirt, chosen, inScope: true, setShirt: (k: ShirtKey) => (setShirtState(k), setChosen(true)) }), [shirt, chosen]);
  // one scope for the whole page (the layout); a page's own scope only adds its class
  if (outer.inScope) return className ? <div className={className}>{children}</div> : <>{children}</>;
  return (
    <Ctx.Provider value={value}>
      <div style={kitStyle(shirt)} className={className}>
        {children}
      </div>
    </Ctx.Provider>
  );
}

export function useShirt() {
  return useContext(Ctx);
}

/** Eight shirts with their names: one tap colours the head, the numerals and the lines. */
export function ShirtPicker({ question, hint, names }: { question: string; hint: string; names: Record<ShirtKey, string> }) {
  const { shirt, setShirt } = useShirt();
  return (
    <fieldset className="min-w-0">
      <legend className="font-slant text-[1.375rem] leading-tight md:text-[1.625rem]">{question}</legend>
      <p className="mt-1 text-[1.0625rem] text-ink-2">{hint}</p>
      <div className="mt-4 grid grid-cols-2 gap-2 min-[480px]:grid-cols-4">
        {SHIRTS.map(([key, hex]) => {
          const on = key === shirt;
          return (
            <label
              key={key}
              className={cn(
                "flex min-h-14 cursor-pointer items-center gap-3 border-2 px-3 py-2 text-[1.0625rem] font-semibold has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-3 has-[:focus-visible]:outline-ink",
                on ? "border-ink bg-ink text-ground" : "border-ink/30 bg-paper/60 hover:border-ink",
              )}
            >
              <input type="radio" name="shirt" value={key} checked={on} onChange={() => setShirt(key)} className="sr-only" />
              <Shirt hex={hex} on={on} />
              <span>{names[key]}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function Shirt({ hex, on }: { hex: string; on: boolean }) {
  return (
    <svg viewBox="0 0 32 28" aria-hidden className="h-7 w-8 shrink-0">
      <path d="M10 1 L3 5 L0 12 L6 14 L7 27 L25 27 L26 14 L32 12 L29 5 L22 1 Q16 6 10 1 Z" fill={hex} stroke={on ? "#ffffff" : "#16171a"} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

/** A link to the demo that carries the chosen colour along. */
export function DemoLink({ href, className, children }: { href: string; className?: string; children: ReactNode }) {
  const { shirt, chosen } = useShirt();
  return (
    <Link href={chosen ? `${href}?kit=${shirt}` : href} className={className}>
      {children}
    </Link>
  );
}

/** «Kostenlos starten»: the app's /einstieg with the language and, once picked, the colour. */
export function StartLink({ appLocale, className, children }: { appLocale: string; className?: string; children: ReactNode }) {
  const { shirt, chosen } = useShirt();
  return (
    <a href={startUrl(appLocale, undefined, chosen ? FARBE[shirt] : undefined)} className={className}>
      {children}
    </a>
  );
}

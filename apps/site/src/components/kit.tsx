"use client";

import Link from "next/link";
import { createContext, type CSSProperties, type KeyboardEvent, type ReactNode, useContext, useEffect, useId, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { DEMO_CLUB, kit, kitVars, SHIRTS } from "@/lib/color";
import { withKit } from "@/lib/links";
import { startUrl } from "@/lib/site";

/** The demo opponent: black with white (TSV Nachtwind). The clash rule decides how it shows. */
export const DEMO_OPPONENT = ["#17191c", "#ffffff"] as const;

export type ShirtKey = (typeof SHIRTS)[number][0];
const KEYS = SHIRTS.map(([k]) => k) as readonly ShirtKey[];

function isShirt(v: string | null): v is ShirtKey {
  return v !== null && (KEYS as readonly string[]).includes(v);
}

function second(hex: string): string {
  return hex === "#ffffff" || hex === "#f6c500" ? "#17191c" : "#ffffff";
}

/** The colours of a picked shirt, or with none picked the demo club's own (the website's green). */
export function kitStyle(key: ShirtKey | null): CSSProperties {
  const hex = key ? SHIRTS.find(([k]) => k === key)![1] : DEMO_CLUB;
  return kitVars(kit([hex, second(hex)], DEMO_OPPONENT)) as CSSProperties;
}

/** German names the app takes as `farbe=` on /einstieg (OPEN_QUESTIONS Q-SITE-9). */
export const FARBE: Record<ShirtKey, string> = { blue: "blau", red: "rot", yellow: "gelb", black: "schwarz", white: "weiss", green: "gruen", orange: "orange", purple: "violett" };

interface KitState {
  /** null: nobody picked a colour, the demo club plays in its own green */
  shirt: ShirtKey | null;
  /** true once the visitor picked a colour (or came with ?kit=): only then it goes to the app */
  chosen: boolean;
  setShirt: (k: ShirtKey) => void;
  inScope: boolean;
}
const Ctx = createContext<KitState>({ shirt: null, chosen: false, setShirt: () => {}, inScope: false });

/**
 * The visitor's colour for the demo match. Starts with the demo club's green (the website's own
 * colour, the same on every page), or with `?kit=` from a link (the start page hands the choice to
 * the demo that way); nothing is stored in the browser.
 */
export function KitScope({ children, className }: { children: ReactNode; className?: string }) {
  const outer = useContext(Ctx);
  const [shirt, setShirtState] = useState<ShirtKey | null>(null);
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
      <legend className="text-[1.375rem] leading-tight font-bold md:text-[1.5rem]">{question}</legend>
      <p className="mt-1 text-[1.0625rem] text-ink-2">{hint}</p>
      <div className="mt-4 grid grid-cols-[repeat(auto-fill,minmax(min(100%,9.75rem),1fr))] gap-2">
        {SHIRTS.map(([key, hex]) => {
          const on = key === shirt;
          return (
            <label
              key={key}
              className={cn(
                "flex min-h-14 min-w-0 cursor-pointer items-center gap-2.5 border-2 px-3 py-2 text-[1.0625rem] font-semibold has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-3 has-[:focus-visible]:outline-ink",
                on ? "border-ink bg-ink text-ground" : "border-ink/30 bg-paper/60 hover:border-ink",
              )}
            >
              <input type="radio" name="shirt" value={key} checked={on} onChange={() => setShirt(key)} className="sr-only" />
              <Shirt hex={hex} on={on} />
              <span className="min-w-0 break-words">{names[key]}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/**
 * The same choice, compact, for the demo page's head (BEFUNDE-4 U42): a button with the current
 * shirt and «Probier deine Vereinsfarbe» (once picked: its name) opens the eight shirts. It shares
 * the state with the picker at the end of the page, so both always show the same colour. Escape,
 * a tap outside or a choice close it, and the focus goes back to the button.
 */
export function ShirtMenu({ label, chosenLabel, names }: { label: string; chosenLabel: string; names: Record<ShirtKey, string> }) {
  const { shirt, chosen, setShirt } = useShirt();
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();
  const hex = shirt ? SHIRTS.find(([k]) => k === shirt)![1] : DEMO_CLUB;
  const text = chosen && shirt ? chosenLabel.replace("{name}", names[shirt]) : label;

  const close = (focus: boolean) => {
    setOpen(false);
    if (focus) button.current?.focus();
  };

  useEffect(() => {
    if (!open) return;
    // the current shirt (or the first) gets the focus
    const items = [...(panel.current?.querySelectorAll<HTMLButtonElement>("button") ?? [])];
    (items.find((b) => b.getAttribute("aria-pressed") === "true") ?? items[0])?.focus();
    const down = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!panel.current?.contains(t) && !button.current?.contains(t)) setOpen(false);
    };
    document.addEventListener("pointerdown", down);
    return () => document.removeEventListener("pointerdown", down);
  }, [open]);

  const keys = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      close(true);
      return;
    }
    const items = [...(panel.current?.querySelectorAll<HTMLButtonElement>("button") ?? [])];
    const i = items.indexOf(document.activeElement as HTMLButtonElement);
    const move = { ArrowDown: 2, ArrowUp: -2, ArrowRight: 1, ArrowLeft: -1, Home: -99, End: 99 }[e.key];
    if (move == null || i < 0) return;
    e.preventDefault();
    items[Math.max(0, Math.min(items.length - 1, i + move))]?.focus();
  };

  return (
    <div className="relative">
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => e.key === "Escape" && open && close(true)}
        className="flex min-h-12 cursor-pointer items-center gap-2.5 border-2 border-ink bg-paper px-3 py-1.5 text-[1.0625rem] font-bold text-ink shadow-[3px_3px_0_var(--ink)] hover:bg-ground"
      >
        <Shirt hex={hex} on={false} />
        <span>{text}</span>
        <svg viewBox="0 0 20 20" aria-hidden className={cn("size-4 shrink-0 transition-transform motion-reduce:transition-none", open && "rotate-180")}>
          <path d="M4 7l6 6 6-6" fill="none" stroke="currentColor" strokeWidth={2.6} />
        </svg>
      </button>
      {open && (
        <div
          ref={panel}
          id={id}
          role="group"
          aria-label={label}
          onKeyDown={keys}
          className="absolute top-full right-0 z-30 mt-2 grid w-[min(22rem,calc(100vw-2rem))] grid-cols-2 gap-1.5 border-2 border-ink bg-paper p-2 text-ink shadow-[6px_6px_0_var(--ink)] max-sm:right-auto max-sm:left-0"
        >
          {SHIRTS.map(([key, h]) => {
            const on = key === shirt;
            return (
              <button
                key={key}
                type="button"
                aria-pressed={on}
                onClick={() => {
                  setShirt(key);
                  close(true);
                }}
                className={cn(
                  "flex min-h-12 min-w-0 cursor-pointer items-center gap-2.5 border-2 px-2.5 text-left text-[1.0625rem] font-semibold",
                  on ? "border-ink bg-ink text-ground" : "border-transparent hover:border-ink",
                )}
              >
                <Shirt hex={h} on={on} />
                <span className="min-w-0 break-words">{names[key]}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
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
    <Link href={chosen && shirt ? withKit(href, shirt) : href} className={className}>
      {children}
    </Link>
  );
}

/** «Kostenlos starten»: the app's /einstieg with the language and, once picked, the colour. */
export function StartLink({ appLocale, className, children }: { appLocale: string; className?: string; children: ReactNode }) {
  const { shirt, chosen } = useShirt();
  return (
    <a href={startUrl(appLocale, undefined, chosen && shirt ? FARBE[shirt] : undefined)} className={className}>
      {children}
    </a>
  );
}

"use client";

import { useEffect, useRef, type RefObject } from "react";

/**
 * Escape closes inline panels too, not only dialogs (finding A15): an open «Mehr» (`<details>`)
 * and the panels that open in the page (Werkbank, Torhüter, a player's status). One Escape closes
 * one thing: the panel around the focus, the innermost first, else the one opened last. A dialog
 * or menu above the page handles its own Escape, and a part of a panel that uses Escape itself
 * (leaving the review, a field being edited) calls `preventDefault()` and keeps its panel open.
 */

interface Entry {
  close: () => void;
  el: RefObject<HTMLElement | null> | undefined;
  /** what had the focus when the panel opened (its button): it gets the focus back */
  opener: Element | null;
}

const stack: Entry[] = [];
let installed = false;

/** something above the page that answers Escape itself */
const LAYER = 'dialog[open], [role="dialog"], [role="alertdialog"], [role="menu"], [role="listbox"]';

/** The panel one Escape closes: around the focus (innermost), else the last opened. */
export function pickEscape(focus: Element | null, entries: readonly { el: Element | null }[], openDetails: Element | null): number | "details" | null {
  let best = -1;
  for (let i = 0; i < entries.length; i++) {
    const el = entries[i]!.el;
    if (!el || !focus || !el.contains(focus)) continue;
    if (best < 0 || entries[best]!.el!.contains(el)) best = i;
  }
  // an open «Mehr» around the focus inside that panel (or with no panel around the focus) first
  if (openDetails && (best < 0 || entries[best]!.el!.contains(openDetails))) return "details";
  if (best >= 0) return best;
  return entries.length ? entries.length - 1 : null;
}

function onKey(e: KeyboardEvent) {
  if (e.key !== "Escape" || e.isComposing || document.querySelector(LAYER)) return;
  const focus = document.activeElement;
  const details = focus?.closest("details[open]") ?? null;
  const pick = pickEscape(
    focus,
    stack.map((s) => ({ el: s.el?.current ?? null })),
    details,
  );
  if (pick == null) return;
  const entry = pick === "details" ? null : stack[pick];
  // after the event has gone everywhere: a part that used Escape itself has said so by then
  window.setTimeout(() => {
    if (e.defaultPrevented) return;
    if (pick === "details" && details instanceof HTMLDetailsElement) {
      details.open = false;
      details.querySelector("summary")?.focus();
    } else if (entry) {
      entry.close();
      // the focus back to the button that opened the panel, once the panel is gone
      requestAnimationFrame(() => {
        if (entry.opener instanceof HTMLElement && entry.opener.isConnected && !entry.el?.current?.contains(entry.opener)) entry.opener.focus();
      });
    }
  }, 0);
}

function install() {
  if (installed || typeof window === "undefined") return;
  installed = true;
  // capture: seen before a dialog closes itself, so its Escape is not taken for the page's
  window.addEventListener("keydown", onKey, true);
}

/** Escape closes an open «Mehr» (`<details>`) around the focus anywhere in the app. */
export function useEscapeDetails() {
  useEffect(install, []);
}

/** While `open`, Escape closes this inline panel (`el`: the panel, to prefer it when it has the focus). */
export function useEscape(open: boolean, close: () => void, el?: RefObject<HTMLElement | null>) {
  const latest = useRef(close);
  useEffect(() => {
    latest.current = close;
  });
  useEffect(() => {
    if (!open) return;
    install();
    const entry: Entry = { close: () => latest.current(), el, opener: document.activeElement };
    stack.push(entry);
    return () => {
      const i = stack.indexOf(entry);
      if (i >= 0) stack.splice(i, 1);
    };
  }, [open, el]);
}

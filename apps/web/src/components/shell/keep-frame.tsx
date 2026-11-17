"use client";

import { useEffect } from "react";
import { useOptionalShell } from "./context";

/** Rendered by the 404 inside the app: the head and the navigation stay, also where the address
 * is a full-screen tool (Prüfen, Spieltag), so the way on is always there (app review R5). */
export function KeepFrame() {
  const show = useOptionalShell()?.showFrame;
  useEffect(() => {
    show?.(true);
    return () => show?.(false);
  }, [show]);
  return null;
}

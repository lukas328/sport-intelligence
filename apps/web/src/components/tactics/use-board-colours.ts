"use client";

import { useMemo } from "react";
import { useOptionalShell } from "@/components/shell/context";
import { boardColours, type BoardColours } from "./board-theme";

/** The board's players in this club's colour (A16); outside the app (a shared link) the board's own. */
export function useBoardColours(): BoardColours {
  const club = useOptionalShell()?.org.primary_color ?? null;
  return useMemo(() => boardColours(club), [club]);
}

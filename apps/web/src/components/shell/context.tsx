"use client";

import { createContext, useContext } from "react";
import type { Mode } from "@/lib/nav-model";

export interface ShellTeam {
  id: string;
  name: string;
  my_role: string | null;
  is_youth: boolean;
  season: string | null;
  season_id: string | null;
  /** "Teamfunktionen" (ADR 029): training, dates, RSVP, tasks, player and parent areas */
  team_features: boolean;
}

export interface ShellOrg {
  id: string;
  name: string;
  has_logo: boolean;
  primary_color: string;
  /** the club's second colour (lib/color.ts kit) */
  secondary_color?: string | null;
  my_role: string;
}

export interface ShellValue {
  org: ShellOrg;
  orgs: { id: string; name: string }[];
  teams: ShellTeam[];
  team: ShellTeam | null;
  mode: Mode;
  me: { name: string; email: string };
  setTeam: (id: string) => void;
}

export const ShellContext = createContext<ShellValue | null>(null);

export function useShell(): ShellValue {
  const v = useContext(ShellContext);
  if (!v) throw new Error("useShell outside the app shell");
  return v;
}

/** Shell, if rendered inside one (shared views also render outside). */
export function useOptionalShell(): ShellValue | null {
  return useContext(ShellContext);
}

export const TEAM_COOKIE = "hb_team";

export function setCookie(name: string, value: string) {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=31536000; samesite=lax`;
}

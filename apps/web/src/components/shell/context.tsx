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
  /** the plan features the club can use now (OrgOut.features), e.g. `goalkeepers` */
  features?: string[];
}

export interface ShellMe {
  name: string;
  email: string;
  /** the club asks for two-factor and it is not set up */
  two_factor_due?: boolean;
  /** past the grace period: club settings are blocked until two-factor is set up */
  two_factor_overdue?: boolean;
}

export interface ShellValue {
  org: ShellOrg;
  orgs: { id: string; name: string }[];
  teams: ShellTeam[];
  team: ShellTeam | null;
  mode: Mode;
  me: ShellMe;
  setTeam: (id: string) => void;
  /** a page that is not there (the 404) asks for the whole app frame, also on a full-screen tool
   * route such as Prüfen (app review R5: a deleted match's «Fragen» link ended without a header) */
  showFrame?: (on: boolean) => void;
  /** a page with its own upload field (a match without video) points the frame's «Video
   * hochladen» there, so the page has one way to upload, not two (finding A11) */
  setPageUpload?: (href: string | null) => void;
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

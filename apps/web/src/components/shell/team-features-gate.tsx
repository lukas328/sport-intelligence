"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";
import { useOptionalShell } from "./context";

/**
 * Pages of the "Teamfunktionen" (dates, own scenes, consents, tasks: SPEC 6). Without the team
 * functions on any team of the club they lead back to Spiele instead of opening in the old frame
 * (UX test B32); the pages themselves stay for the clubs that switch them on.
 */
export function TeamFeaturesGate({ children }: { children: ReactNode }) {
  const shell = useOptionalShell();
  const router = useRouter();
  // players and parents always reach their pages; staff only with the team functions on
  const on = !shell || shell.mode !== "staff" || shell.teams.some((t) => t.team_features);
  useEffect(() => {
    if (shell && !on) router.replace(`/app/${shell.org.id}`);
  }, [shell, on, router]);
  return on ? <>{children}</> : null;
}

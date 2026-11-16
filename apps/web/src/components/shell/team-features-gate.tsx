"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";
import { useOptionalShell } from "./context";
import { LifeHint } from "./life-hint";
import { AreaSubNav } from "./section-nav";

/**
 * Pages of «Teamleben» (the team setting "Teamfunktionen": dates, own scenes, consents, tasks;
 * SPEC 6, finding K16). Without it on any team of the club they lead back to Spiele instead of
 * opening in the old frame (UX test B32); the pages themselves stay for the clubs that switch it on.
 * Parents always reach their pages; players reach their own consents (the profile links there).
 * `tabs`: the Teamleben tabs above a page that has none of its own.
 */
export function TeamFeaturesGate({ children, tabs = false, forPlayers = false }: { children: ReactNode; tabs?: boolean; forPlayers?: boolean }) {
  const shell = useOptionalShell();
  const router = useRouter();
  const on =
    !shell || shell.mode === "family" || (forPlayers && shell.mode === "player") || shell.teams.some((t) => t.team_features);
  useEffect(() => {
    if (shell && !on) router.replace(`/app/${shell.org.id}`);
  }, [shell, on, router]);
  if (!on) return null;
  return (
    <>
      {tabs && shell && (
        <div className="mb-6 space-y-5">
          <AreaSubNav />
          <LifeHint />
        </div>
      )}
      {children}
    </>
  );
}

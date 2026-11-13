"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";

/**
 * «Link kopieren»: creates the team's consent link (SPEC 7.10, one link for the team chat) and
 * puts it on the clipboard. Where the clipboard is not allowed, the link is shown to select.
 */
export function ConsentCopy({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("teamPage");
  const [state, setState] = useState<"idle" | "busy" | "copied" | "shown">("idle");
  const [url, setUrl] = useState<string | null>(null);
  async function copy() {
    setState("busy");
    const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/consent-link", { params: { path: { org_id: orgId, team_id: teamId } } });
    if (!r.data) return setState("idle");
    const link = `${window.location.origin}/einwilligung/${r.data.token}`;
    setUrl(link);
    try {
      await navigator.clipboard.writeText(link);
      setState("copied");
    } catch {
      setState("shown");
    }
  }
  return (
    <div className="mt-4 space-y-2" data-testid="consent-link">
      <Button onClick={() => void copy()} loading={state === "busy"}>
        {state === "copied" ? t("copied") : t("copyLink")}
      </Button>
      <p role="status" className="text-[15px] text-ink-2">
        {state === "shown" && t("copyFailed")}
      </p>
      {state === "shown" && url && (
        <input readOnly value={url} onFocus={(e) => e.currentTarget.select()} className="w-full border-[1.5px] border-ink bg-transparent px-2 py-2 font-mono text-xs" data-testid="consent-link-url" />
      )}
    </div>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";
import { errorKey } from "@/lib/errors";

/** Creates a read-only public link (play, match report or playlist) and shows it once. */
export function ShareButton({ orgId, teamId, kind, targetId }: { orgId: string; teamId: string; kind: "play" | "match" | "playlist" | "highlight"; targetId: string }) {
  const t = useTranslations("share");
  const te = useTranslations("errors");
  const [open, setOpen] = useState(false);
  const [days, setDays] = useState(14);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  async function create() {
    const { data, error: err } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/share-links", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: { kind, target_id: targetId, days },
    });
    if (err || !data) return setError(te(errorKey(err)));
    setError(null);
    setUrl(`${window.location.origin}/s/${data.token}`);
  }
  return (
    <div className="relative inline-block">
      <Button variant="secondary" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {t("button")}
      </Button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-80 max-w-[90vw] space-y-2 rounded-lg border border-border bg-background p-3 text-sm shadow-lg" role="dialog" aria-label={t("title")}>
          <p className="font-semibold">{t("title")}</p>
          <p className="text-xs text-muted">{t("hint")}</p>
          {!url ? (
            <div className="flex items-end gap-2">
              <label className="flex flex-col gap-1">
                {t("valid")}
                <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="min-h-9 rounded-md border border-border bg-background px-2">
                  {[1, 7, 14, 30, 90].map((d) => (
                    <option key={d} value={d}>
                      {t("days", { count: d })}
                    </option>
                  ))}
                </select>
              </label>
              <Button onClick={() => void create()}>{t("create")}</Button>
            </div>
          ) : (
            <div className="space-y-2">
              <label className="flex flex-col gap-1">
                {t("link")}
                <input readOnly value={url} onFocus={(e) => e.currentTarget.select()} className="min-h-9 rounded-md border border-border bg-surface px-2 font-mono text-xs" data-testid="share-url" />
              </label>
              <Button
                variant="secondary"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(url);
                    setCopied(true);
                  } catch {
                    setCopied(false);
                  }
                }}
              >
                {copied ? t("copied") : t("copy")}
              </Button>
            </div>
          )}
          {error && <p className="text-error">{error}</p>}
        </div>
      )}
    </div>
  );
}

"use client";

import { Check, Copy, Share2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { control } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey } from "@/lib/errors";
import { cn } from "@/lib/utils";

/** Creates a read-only public link (play, match report or playlist) and shows it once. */
export function ShareButton({ orgId, teamId, kind, targetId }: { orgId: string; teamId: string; kind: "play" | "match" | "playlist" | "highlight"; targetId: string }) {
  const t = useTranslations("share");
  const te = useTranslations("errors");
  const [days, setDays] = useState(14);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  async function create() {
    setBusy(true);
    const { data, error: err } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/share-links", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: { kind, target_id: targetId, days },
    });
    setBusy(false);
    if (err || !data) return setError(te(errorKey(err)));
    setError(null);
    setUrl(`${window.location.origin}/s/${data.token}`);
  }
  return (
    <Dialog
      title={t("title")}
      description={t("hint")}
      onOpenChange={(o) => !o && (setUrl(null), setCopied(false))}
      trigger={
        <Button variant="secondary">
          <Share2 aria-hidden />
          {t("button")}
        </Button>
      }
    >
      {!url ? (
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-[0.8125rem] font-medium">
            {t("valid")}
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} className={cn(control, "w-40")}>
              {[1, 7, 14, 30, 90].map((d) => (
                <option key={d} value={d}>
                  {t("days", { count: d })}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={() => void create()} loading={busy}>
            {t("create")}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <label className="flex flex-col gap-1 text-[0.8125rem] font-medium">
            {t("link")}
            <input readOnly value={url} onFocus={(e) => e.currentTarget.select()} className={cn(control, "font-mono text-xs")} data-testid="share-url" />
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
            {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
            {copied ? t("copied") : t("copy")}
          </Button>
        </div>
      )}
      {error && <Alert className="mt-3">{error}</Alert>}
    </Dialog>
  );
}

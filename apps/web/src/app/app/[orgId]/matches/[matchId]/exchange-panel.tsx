"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button, buttonClass } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

/** Sportscode XML and CSV export, Sportscode XML import as own tags (addendum 01, 5.4). */
export function ExchangePanel({ orgId, matchId, canImport }: { orgId: string; matchId: string; canImport: boolean }) {
  const t = useTranslations("exchange");
  const tr = useTranslations();
  const qc = useQueryClient();
  const [result, setResult] = useState<{ clips: number; tags_created: number } | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [busy, setBusy] = useState(false);
  const base = `/v1/orgs/${orgId}/matches/${matchId}`;
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const file = (e.currentTarget.elements.namedItem("file") as HTMLInputElement).files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    const body = new FormData();
    body.append("file", file);
    const r = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/import/sportscode", {
      params: { path: { org_id: orgId, match_id: matchId } },
      body: body as unknown as { file: string },
      bodySerializer: (x) => x as unknown as FormData,
    });
    setBusy(false);
    if (r.error || !r.data) {
      setError(errorKey(r.error));
      return;
    }
    setResult(r.data as { clips: number; tags_created: number });
    void qc.invalidateQueries({ queryKey: ["clips", matchId] });
  };
  const link = buttonClass("secondary", "sm");
  return (
    <div data-testid="exchange">
      <div className="space-y-5">
        <div className="flex flex-wrap gap-2">
          <a className={link} href={`${base}/export/sportscode`} data-testid="export-xml">
            {t("sportscode")}
          </a>
          <a className={link} href={`${base}/export/events`} data-testid="export-csv">
            {t("csv")}
          </a>
        </div>
        <p className="text-sm text-muted">{t("exportHint")}</p>
        {canImport && (
          <form onSubmit={submit} className="space-y-2">
            <label className="block text-sm font-medium">
              {t("importLabel")}
              <input name="file" type="file" accept=".xml,application/xml,text/xml" required className="mt-1 block text-sm text-muted file:mr-3 file:rounded-full file:border-0 file:bg-surface file:px-3 file:py-1.5 file:text-foreground" />
            </label>
            <p className="text-xs text-muted">{t("importHint")}</p>
            <Button type="submit" disabled={busy}>
              {t("import")}
            </Button>
            {result && <p className="text-sm text-ok">{t("imported", { clips: result.clips, tags: result.tags_created })}</p>}
            {error && <Alert>{tr(`errors.${error}`)}</Alert>}
          </form>
        )}
      </div>
    </div>
  );
}

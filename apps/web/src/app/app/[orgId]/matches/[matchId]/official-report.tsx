"use client";

import type { Schemas } from "@handball/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Result = Schemas["OfficialReportResult"];

/** Official match report by link (handball.ch match centre, DHB press report, nuLiga game report,
 * HLA report): goals with scorer, 7-metres, suspensions and time-outs become events; a new import
 * replaces the previous one. The API's warnings are shown as they come (the HLA report has no
 * timed goals and points to the ÖHB nuLiga report). */
export function OfficialReportImport({ orgId, matchId }: { orgId: string; matchId: string }) {
  const t = useTranslations("officialReport");
  const tr = useTranslations();
  const qc = useQueryClient();
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const url = (e.currentTarget.elements.namedItem("url") as HTMLInputElement).value.trim();
    if (!url) return;
    setBusy(true);
    setError(null);
    setResult(null);
    const r = await api.POST("/v1/orgs/{org_id}/matches/{match_id}/official-report", {
      params: { path: { org_id: orgId, match_id: matchId } },
      body: { url },
    });
    setBusy(false);
    if (r.error || !r.data) return setError(errorKey(r.error));
    setResult(r.data);
    for (const key of ["events", "stats", "match", "official-goals"]) void qc.invalidateQueries({ queryKey: [key, matchId] });
  };

  return (
    <form onSubmit={submit} className="space-y-2 border-t border-foreground/15 pt-5" data-testid="official-report">
      <Input
        name="url"
        label={t("label")}
        hint={t("hint")}
        inputMode="url"
        autoComplete="off"
        spellCheck={false}
        placeholder="https://www.handball.ch/de/matchcenter/spiele/…"
        required
      />
      <Button type="submit" disabled={busy} aria-busy={busy}>
        {busy ? t("importing") : t("import")}
      </Button>
      <div aria-live="polite" className="space-y-2">
        {result && (
          <Alert kind="success">
            <p>{t("imported", { created: result.created, matched: result.matched_video_goals })}</p>
            {result.home && result.away && (
              <p className="text-muted">
                {`${result.home} ${tr("matches.vs")} ${result.away}`}
                {result.final ? ` ${result.final[0]}:${result.final[1]}` : ""}
              </p>
            )}
            {result.warnings.length > 0 && <p className="mt-1 font-medium">{t("warnings")}</p>}
            {result.warnings.length > 0 && (
              <ul className="list-disc pl-4 text-muted">
                {result.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}
          </Alert>
        )}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </div>
    </form>
  );
}

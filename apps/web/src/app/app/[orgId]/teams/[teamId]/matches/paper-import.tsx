"use client";

import { FileUp } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type ChangeEvent } from "react";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

/** Paper match report (JSON per docs/schemas/paper-report.schema.json) as a match without video. */
export function PaperImport({ orgId, teamId, onWarnings }: { orgId: string; teamId: string; onWarnings: (w: string[]) => void }) {
  const t = useTranslations();
  const router = useRouter();
  const [failure, setFailure] = useState<ErrorKey | null>(null);

  async function onFile(e: ChangeEvent<HTMLInputElement>) {
    const input = e.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    const { data, error } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/paper-reports", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: body as unknown as { file: string },
      bodySerializer: (b) => b as unknown as FormData,
    });
    input.value = "";
    if (error || !data) return setFailure(errorKey(error));
    setFailure(null);
    const result = data as { match_id: string; warnings: string[] };
    onWarnings(result.warnings);
    if (result.warnings.length === 0) router.push(`/app/${orgId}/matches/${result.match_id}`);
    else router.refresh();
  }

  return (
    <>
      <label className="inline-flex cursor-pointer items-center gap-1.5 font-medium text-foreground hover:text-accent focus-within:outline-2 focus-within:outline-accent" title={t("paper.hint")}>
        <FileUp aria-hidden className="size-4" />
        {t("matches.importFile")}
        <input type="file" accept=".json,application/json" onChange={onFile} data-testid="paper-file" className="sr-only" aria-describedby="paper-hint" />
      </label>
      <span id="paper-hint" className="sr-only">
        {t("paper.hint")}
      </span>
      {failure && <Alert className="w-full">{t(`errors.${failure}`)}</Alert>}
    </>
  );
}

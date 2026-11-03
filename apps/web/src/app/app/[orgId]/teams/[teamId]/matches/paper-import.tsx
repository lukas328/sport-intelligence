"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type ChangeEvent } from "react";
import { Alert, Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

/** Paper match report (JSON per docs/schemas/paper-report.schema.json) as a match without video. */
export function PaperImport({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations();
  const router = useRouter();
  const [failure, setFailure] = useState<ErrorKey | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

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
    setWarnings(result.warnings);
    if (result.warnings.length === 0) router.push(`/app/${orgId}/matches/${result.match_id}`);
    else router.refresh();
  }

  return (
    <Card className="space-y-3">
      <h2 className="text-lg font-semibold">{t("paper.title")}</h2>
      <p className="text-sm text-muted">{t("paper.hint")}</p>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">{t("paper.file")}</span>
        <input type="file" accept=".json,application/json" onChange={onFile} data-testid="paper-file" />
      </label>
      {failure && <Alert>{t(`errors.${failure}`)}</Alert>}
      {warnings.length > 0 && (
        <Alert kind="info">
          <p className="font-medium">
            {t("paper.done")} {t("paper.warnings")}:
          </p>
          <ul className="list-disc pl-5">
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Alert>
      )}
    </Card>
  );
}

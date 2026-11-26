"use client";

import type { Schemas } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useId, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { parseQuickRoster, quickCsv } from "@/lib/roster-numbers";
import { cn } from "@/lib/utils";

type ImportResult = Schemas["ImportResult"];

/**
 * The squad in one go: number and name per line, typed on the phone or pasted from a list or a
 * spreadsheet. The lines are read as they are typed (what is wrong shows at once); «Übernehmen»
 * sends them through the squad import, which checks again (numbers already taken in the season).
 */
export function QuickRoster({ path, onImported }: { path: { org_id: string; team_id: string; season_id: string }; onImported: (count: number) => void }) {
  const t = useTranslations("roster");
  const id = useId();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [server, setServer] = useState<ImportResult | null>(null);
  const rows = useMemo(() => parseQuickRoster(text), [text]);
  const good = rows.filter((r) => !r.error);
  const noNumber = good.filter((r) => r.number == null).length;
  async function save() {
    if (!good.length) return;
    setBusy(true);
    const body = new FormData();
    body.append("file", new Blob([quickCsv(rows)], { type: "text/csv" }), "kader.csv");
    const { data } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster/import", {
      params: { path, query: { dry_run: false } },
      body: body as unknown as { file: string },
      bodySerializer: (b) => b as unknown as FormData,
    });
    setBusy(false);
    if (!data) return;
    if (data.created > 0) {
      setText("");
      setServer(data.errors.length ? data : null);
      onImported(data.created);
    } else setServer(data);
  }
  return (
    <div className="space-y-3" data-testid="quick-roster">
      <label htmlFor={id} className="block text-[15px] font-semibold">
        {t("quickLabel")}
      </label>
      <p className="m-0 text-sm text-muted" id={`${id}-hint`}>
        {t("quickHint")}
      </p>
      <textarea
        id={id}
        aria-describedby={`${id}-hint`}
        value={text}
        onChange={(e) => (setText(e.target.value), setServer(null))}
        rows={6}
        autoComplete="off"
        autoCapitalize="words"
        spellCheck={false}
        placeholder={"7 Lena Muster\n10 Mia Beispiel\n12 Noa Probst"}
        className="block w-full bg-raised px-3 py-2 text-base ring-1 ring-inset ring-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        data-testid="quick-roster-text"
      />
      {rows.length > 0 && (
        <ul className="m-0 max-h-56 list-none space-y-1 overflow-auto p-0 text-[15px]" aria-label={t("quickPreview")} data-testid="quick-roster-preview">
          {rows.map((r) => (
            <li key={r.line} className={cn("flex gap-2", r.error && "text-error")}>
              <span className="w-8 shrink-0 text-right font-num tabular-nums">{r.number ?? "–"}</span>
              <span className="min-w-0 flex-1 truncate">{r.error === "name" ? t("quickNeedsName", { line: r.line }) : `${r.first} ${r.last}`}</span>
              {r.error && r.error !== "name" && <span className="shrink-0 text-sm">{t(r.error === "twice" ? "quickTwice" : "quickBadNumber")}</span>}
            </li>
          ))}
        </ul>
      )}
      {noNumber > 0 && (
        <p className="m-0 text-sm" data-testid="quick-roster-nonumber">
          {t("quickNoNumber", { n: noNumber })}
        </p>
      )}
      {server && server.errors.length > 0 && (
        <Alert>
          <ul className="list-disc pl-4">
            {server.errors.map((e, i) => (
              <li key={i}>{t("csvRowError", { row: e.row - 1, message: e.message })}</li>
            ))}
          </ul>
        </Alert>
      )}
      <Button className="max-sm:w-full" disabled={!good.length} loading={busy} onClick={() => void save()} data-testid="quick-roster-save">
        {t("quickSave", { count: good.length })}
      </Button>
    </div>
  );
}

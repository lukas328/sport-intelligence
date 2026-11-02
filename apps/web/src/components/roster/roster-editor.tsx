"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card, EmptyState } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Entry = Schemas["RosterEntryOut"];
type ImportResult = Schemas["ImportResult"];

const POSITIONS = ["LA", "RL", "RM", "RR", "RA", "KM", "TW"] as const;
const TEMPLATE = "Vorname;Nachname;Nr;Position;Wurfhand;Jahrgang\nLena;Meier;7;RA;links;2004\n";

interface Props {
  orgId: string;
  teamId: string;
  seasonId: string;
  canEdit: boolean;
}

export function RosterEditor({ orgId, teamId, seasonId, canEdit }: Props) {
  const t = useTranslations();
  const qc = useQueryClient();
  const path = { org_id: orgId, team_id: teamId, season_id: seasonId };
  const key = ["roster", seasonId];
  const roster = useQuery({
    queryKey: key,
    queryFn: async () => {
      const { data, error } = await api.GET("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", {
        params: { path },
      });
      if (error) throw error;
      return data;
    },
  });
  const [error, setError] = useState<ErrorKey | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  const add = useMutation({
    mutationFn: async (body: Schemas["RosterEntryCreate"]) => {
      const { data, error } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster", {
        params: { path },
        body,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: (entry) => {
      setError(null);
      setNotice(t("roster.added", { name: `${entry.first_name} ${entry.last_name}` }));
      formRef.current?.reset();
      formRef.current?.querySelector<HTMLInputElement>("input[name=jersey_number]")?.focus();
      void qc.invalidateQueries({ queryKey: key });
    },
    onError: (e) => setError(errorKey(e)),
  });

  const remove = useMutation({
    mutationFn: async (entryId: string) => {
      const { error } = await api.DELETE("/v1/orgs/{org_id}/teams/{team_id}/roster/{entry_id}", {
        params: { path: { org_id: orgId, team_id: teamId, entry_id: entryId } },
      });
      if (error) throw error;
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: key }),
    onError: (e) => setError(errorKey(e)),
  });

  function onAdd(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const num = String(f.get("jersey_number") ?? "").trim();
    const year = String(f.get("birth_year") ?? "").trim();
    const pos = String(f.get("main_position") ?? "");
    const hand = String(f.get("shooting_hand") ?? "");
    setNotice(null);
    add.mutate({
      first_name: String(f.get("first_name")),
      last_name: String(f.get("last_name")),
      jersey_number: num ? Number(num) : null,
      birth_year: year ? Number(year) : null,
      main_position: pos ? (pos as Entry["main_position"]) : null,
      shooting_hand: hand ? (hand as Entry["shooting_hand"]) : null,
    });
  }

  const entries = roster.data ?? [];
  return (
    <div className="space-y-6">
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      <section aria-labelledby="roster-list" className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h2 id="roster-list" className="text-lg font-semibold">
            {t("roster.title")}
          </h2>
          <span className="text-sm text-muted" data-testid="roster-count">
            {t("roster.count", { count: entries.length })}
          </span>
        </div>
        {roster.isLoading ? (
          <p className="text-muted">{t("common.loading")}</p>
        ) : entries.length === 0 ? (
          <EmptyState title={t("roster.empty")}>{canEdit && t("roster.emptyHint")}</EmptyState>
        ) : (
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface text-muted">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium">{t("roster.number")}</th>
                  <th scope="col" className="px-3 py-2 font-medium">{t("roster.lastName")}</th>
                  <th scope="col" className="px-3 py-2 font-medium">{t("roster.firstName")}</th>
                  <th scope="col" className="px-3 py-2 font-medium">{t("roster.position")}</th>
                  <th scope="col" className="hidden px-3 py-2 font-medium sm:table-cell">{t("roster.hand")}</th>
                  <th scope="col" className="hidden px-3 py-2 font-medium sm:table-cell">{t("roster.account")}</th>
                  {canEdit && <th scope="col" className="px-3 py-2"><span className="sr-only">{t("common.edit")}</span></th>}
                </tr>
              </thead>
              <tbody>
                {entries.map((p) => (
                  <tr key={p.id} className="border-t border-border" data-testid="roster-row">
                    <td className="px-3 py-2 tabular-nums">{p.jersey_number ?? ""}</td>
                    <td className="px-3 py-2 font-medium">{p.last_name}</td>
                    <td className="px-3 py-2">{p.first_name}</td>
                    <td className="px-3 py-2" title={p.main_position ? t(`positions.${p.main_position}`) : undefined}>
                      {p.main_position ?? ""}
                    </td>
                    <td className="hidden px-3 py-2 sm:table-cell">{p.shooting_hand ? t(`hands.${p.shooting_hand}`) : ""}</td>
                    <td className="hidden px-3 py-2 text-muted sm:table-cell">
                      {p.has_account ? t("roster.hasAccount") : t("roster.noAccount")}
                    </td>
                    {canEdit && (
                      <td className="px-3 py-2 text-right">
                        <Button
                          variant="ghost"
                          className="min-h-8 px-2 py-1 text-error"
                          aria-label={`${t("roster.remove")}: ${p.first_name} ${p.last_name}`}
                          onClick={() => {
                            if (window.confirm(t("roster.removeConfirm", { name: `${p.first_name} ${p.last_name}` })))
                              remove.mutate(p.id);
                          }}
                        >
                          {t("roster.remove")}
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {canEdit && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <h3 className="mb-4 font-semibold">{t("roster.addTitle")}</h3>
            <form ref={formRef} onSubmit={onAdd} className="grid grid-cols-2 gap-3" aria-label={t("roster.addTitle")}>
              <Input label={t("roster.number")} name="jersey_number" type="number" min={1} max={99} inputMode="numeric" />
              <Select label={t("roster.position")} name="main_position" defaultValue="">
                <option value="">{t("roster.none")}</option>
                {POSITIONS.map((p) => (
                  <option key={p} value={p}>
                    {p} · {t(`positions.${p}`)}
                  </option>
                ))}
              </Select>
              <Input label={t("roster.firstName")} name="first_name" required autoComplete="off" />
              <Input label={t("roster.lastName")} name="last_name" required autoComplete="off" />
              <Select label={t("roster.hand")} name="shooting_hand" defaultValue="">
                <option value="">{t("roster.none")}</option>
                <option value="right">{t("hands.right")}</option>
                <option value="left">{t("hands.left")}</option>
              </Select>
              <Input label={t("roster.birthYear")} name="birth_year" type="number" min={1940} max={2030} />
              <div className="col-span-2">
                <Button type="submit" loading={add.isPending}>
                  {t("common.add")}
                </Button>
              </div>
            </form>
          </Card>
          <CsvImport path={path} onImported={() => void qc.invalidateQueries({ queryKey: key })} />
        </div>
      )}
    </div>
  );
}

function CsvImport({
  path,
  onImported,
}: {
  path: { org_id: string; team_id: string; season_id: string };
  onImported: () => void;
}) {
  const t = useTranslations();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<number | null>(null);

  async function run(dryRun: boolean) {
    if (!file) return;
    setBusy(true);
    const body = new FormData();
    body.append("file", file);
    const { data } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/seasons/{season_id}/roster/import", {
      params: { path, query: { dry_run: dryRun } },
      body: body as unknown as { file: string },
      bodySerializer: (b) => b as unknown as FormData,
    });
    setBusy(false);
    if (!data) return;
    setResult(data);
    if (!dryRun && data.created > 0) {
      setDone(data.created);
      setResult(null);
      setFile(null);
      onImported();
    }
  }

  const templateHref = `data:text/csv;charset=utf-8,${encodeURIComponent(TEMPLATE)}`;
  return (
    <Card className="space-y-3">
      <h3 className="font-semibold">{t("roster.csvTitle")}</h3>
      <p className="text-sm text-muted">{t("roster.csvHint")}</p>
      <a href={templateHref} download="kader-vorlage.csv" className="text-sm text-accent underline underline-offset-4">
        {t("roster.csvTemplate")}
      </a>
      <Input
        label={t("roster.csvFile")}
        type="file"
        accept=".csv,text/csv"
        onChange={(e) => {
          setFile(e.target.files?.[0] ?? null);
          setResult(null);
          setDone(null);
        }}
      />
      {done !== null && <Alert kind="success">{t("roster.csvImported", { count: done })}</Alert>}
      {result && result.errors.length > 0 && (
        <Alert>
          <ul className="list-inside list-disc">
            {result.errors.map((e, i) => (
              <li key={i}>{t("roster.csvRowError", { row: e.row, message: e.message })}</li>
            ))}
          </ul>
        </Alert>
      )}
      {result && result.errors.length === 0 && (
        <ul className="max-h-40 overflow-auto text-sm" data-testid="csv-preview">
          {result.rows.map((r, i) => (
            <li key={i}>
              {r.jersey_number ?? ""} {r.first_name} {r.last_name} {r.main_position ?? ""}
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <Button variant="secondary" disabled={!file} loading={busy && !result} onClick={() => run(true)}>
          {t("roster.csvCheck")}
        </Button>
        {result && result.errors.length === 0 && (
          <Button loading={busy} onClick={() => run(false)}>
            {t("roster.csvImport", { count: result.rows.length })}
          </Button>
        )}
      </div>
    </Card>
  );
}

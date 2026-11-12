"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AccountLine, UnlinkedAccounts, useTeamMembers } from "./account-link";
import { ConsentLinkBox } from "./consent-link";
import { ConsentOverview } from "./consent-overview";
import { useOptionalShell } from "@/components/shell/context";
import { StatusEditor, StatusLine } from "./player-status";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { FileUp, Trash2, UserPlus, Users } from "lucide-react";
import { Alert, Card, EmptyState, Skeleton } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useConfirm } from "@/components/ui/confirm";
import { Dialog } from "@/components/ui/dialog";
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
  /** onboarding: forms always visible; team page: forms in dialogs once players exist */
  layout?: "inline" | "page";
}

const GROUPS = [
  ["goal", ["TW"]],
  ["back", ["RL", "RM", "RR"]],
  ["wing", ["LA", "RA"]],
  ["pivot", ["KM"]],
  ["other", []],
] as const satisfies readonly (readonly [string, readonly string[]])[];
const ALL_POSITIONS: string[] = GROUPS.flatMap(([, ps]) => [...ps]);

export function RosterEditor({ orgId, teamId, seasonId, canEdit, layout = "page" }: Props) {
  const t = useTranslations();
  const confirm = useConfirm();
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
  // phones: removing players is an edit mode, not a trash can on every row
  const [editing, setEditing] = useState(false);
  // the player whose status (injured, absent) is being set
  const [statusFor, setStatusFor] = useState<string | null>(null);
  const teamMembers = useTeamMembers(orgId, teamId, canEdit);
  // the onboarding renders the squad outside the app shell: the editing coach is staff there
  const shell = useOptionalShell();
  const staffView = shell ? shell.mode === "staff" : canEdit;
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
  const inline = layout === "inline" || (!roster.isLoading && entries.length === 0);
  const addForm = (
    <form ref={formRef} onSubmit={onAdd} className="grid grid-cols-1 gap-3 sm:grid-cols-2" aria-label={t("roster.addTitle")}>
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
      <div className="pt-1 sm:col-span-2">
        <Button type="submit" loading={add.isPending}>
          {t("common.add")}
        </Button>
      </div>
    </form>
  );
  const csv = <CsvImport path={path} onImported={() => void qc.invalidateQueries({ queryKey: key })} />;
  return (
    <div className="space-y-6">
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      <section aria-labelledby="roster-list" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-baseline gap-3">
            {/* on the squad page the H1 already says "Team": the count is enough here */}
            <h2 id="roster-list" className={cn("text-lg font-semibold", !inline && "sr-only")}>
              {t("roster.title")}
            </h2>
            <span className="text-sm text-muted" data-testid="roster-count">
              {t("roster.count", { count: entries.length })}
            </span>
          </div>
          {canEdit && !inline && (
            <div className="flex flex-wrap gap-2">
              {entries.length > 0 && (
                <Button variant="ghost" size="sm" className="lg:hidden" aria-pressed={editing} onClick={() => setEditing((v) => !v)}>
                  {editing ? t("roster.editDone") : t("roster.editList")}
                </Button>
              )}
              <Dialog
                title={t("roster.addTitle")}
                trigger={
                  <Button size="sm">
                    <UserPlus aria-hidden />
                    {t("roster.addTitle")}
                  </Button>
                }
              >
                {error && <Alert className="mb-4">{t(`errors.${error}`)}</Alert>}
                {notice && <Alert kind="success" className="mb-4">{notice}</Alert>}
                {addForm}
              </Dialog>
              <Dialog
                title={t("roster.csvTitle")}
                trigger={
                  <Button size="sm" variant="secondary">
                    <FileUp aria-hidden />
                    {t("roster.csvTitle")}
                  </Button>
                }
              >
                {csv}
              </Dialog>
            </div>
          )}
        </div>
        {roster.isLoading ? (
          <Skeleton className="h-48" />
        ) : entries.length === 0 ? (
          canEdit && inline ? (
            <p className="text-[0.9375rem] text-muted">{t("roster.emptyHint")}</p>
          ) : (
            <EmptyState icon={<Users />} title={t("roster.empty")}>{canEdit && t("roster.emptyHint")}</EmptyState>
          )
        ) : (
          // the squad as it lines up on the match sheet: by position, shirt number first in the club colour
          <div className="space-y-8">
            {canEdit && inline && (
              <Button variant="ghost" size="sm" className="lg:hidden" aria-pressed={editing} onClick={() => setEditing((v) => !v)}>
                {editing ? t("roster.editDone") : t("roster.editList")}
              </Button>
            )}
            {/* for the next unit or match: who is available, and who is out, in one line */}
            {(() => {
              const out = entries.filter((p) => p.status);
              if (out.length === 0) return null;
              return (
                <p className="text-sm" data-testid="roster-availability">
                  <span className="font-semibold">{t("roster.available", { n: entries.length - out.length, total: entries.length })}</span>
                  <span className="text-muted">{` · ${out.map((p) => `${p.first_name} ${p.last_name}`).join(", ")} ${t("roster.out", { n: out.length })}`}</span>
                </p>
              );
            })()}
            {canEdit && teamMembers.data && <UnlinkedAccounts orgId={orgId} teamId={teamId} entries={entries} members={teamMembers.data} rosterKey={key} />}
            {/* before filming: who still lacks a consent, in one sentence (staff only) */}
            {canEdit && (() => {
              const missing = entries.filter((p) => !p.consent_complete);
              return (
                <p className="text-sm" data-testid="roster-consents">
                  {missing.length === 0 ? (
                    <span className="text-muted">{t("roster.consentsAll", { n: entries.length })}</span>
                  ) : (
                    <>
                      <span className="font-semibold">{t("roster.consentsMissing", { n: missing.length, total: entries.length })}</span>{" "}
                      <span className="text-muted">{missing.map((p) => `${p.first_name} ${p.last_name}`).join(", ")}</span>
                    </>
                  )}
                </p>
              );
            })()}
            {/* staff read it before filming (analysts too, read only); the API answers 403 for others
                and the section stays hidden */}
            {staffView && <ConsentOverview orgId={orgId} teamId={teamId} seasonId={seasonId} />}
            {staffView && <ConsentLinkBox orgId={orgId} teamId={teamId} />}
            {GROUPS.map(([g, positions]) => {
              const members = entries.filter((p) => (g === "other" ? !ALL_POSITIONS.includes(p.main_position ?? "") : (positions as readonly string[]).includes(p.main_position ?? "")));
              if (members.length === 0) return null;
              return (
                <section key={g} aria-labelledby={`group-${g}`}>
                  <h3 id={`group-${g}`} className="font-slant mb-1 flex items-baseline gap-2.5 pb-2 text-xl">
                    {t(`roster.group_${g}`)}
                    <span className="font-sans text-sm font-medium text-muted tabular-nums">{members.length}</span>
                  </h3>
                  <ul className="grid border-t-2 border-ink sm:grid-cols-2 sm:gap-x-8 xl:grid-cols-3">
                    {members.map((p) => (
              <li key={p.id} className={cn("group relative flex flex-wrap items-center gap-x-4 gap-y-3 border-b border-foreground/15 py-3.5 pr-1", statusFor === p.player_id && "sm:col-span-2 xl:col-span-3")} data-testid="roster-row">
                <span className={cn("w-14 shrink-0 text-right font-num text-[48px] leading-[.8]", p.status ? "text-ink-2" : "text-club-text")} aria-label={`${t("roster.number")} ${p.jersey_number ?? ""}`}>
                  {p.jersey_number ?? "–"}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="font-slant block truncate text-xl leading-tight">
                    {/* staff open a player's season line from the name */}
                    {canEdit ? (
                      <Link href={`/app/${orgId}/teams/${teamId}/players/${p.player_id}`} className="hover:underline hover:underline-offset-4">
                        {p.first_name} {p.last_name}
                      </Link>
                    ) : (
                      <>
                        {p.first_name} {p.last_name}
                      </>
                    )}
                  </span>
                  <span className="mt-0.5 flex flex-wrap items-center gap-x-2 text-sm text-muted">
                    {p.main_position && (
                      <span className="text-xs font-bold text-foreground" title={t(`positions.${p.main_position}`)}>
                        {p.main_position}
                      </span>
                    )}
                    {p.shooting_hand && <span>{t(`roster.hand_${p.shooting_hand as "left"}`)}</span>}
                    <StatusLine status={p.status} />
                    {/* missing consents are summed up above the list, not repeated on every row */}
                    {/* whether a player has an account is staff business */}
                    {canEdit &&
                      (p.has_account ? (
                        <span className="inline-flex items-center gap-1.5">
                          <span aria-hidden className="size-1.5 rounded-full bg-ok" />
                          {t("roster.hasAccount")}
                        </span>
                      ) : (
                        <span className="sr-only">{t("roster.noAccount")}</span>
                      ))}
                  </span>
                </span>
                {canEdit && (
                  <Button
                    variant="secondary"
                    size="sm"
                    className={cn("max-lg:min-h-11", statusFor !== p.player_id && !p.status && "lg:opacity-0 lg:group-hover:opacity-100 lg:focus-visible:opacity-100")}
                    aria-expanded={statusFor === p.player_id}
                    aria-label={`${t("playerStatus.set")}: ${p.first_name} ${p.last_name}`}
                    onClick={() => setStatusFor(statusFor === p.player_id ? null : p.player_id)}
                  >
                    {t("playerStatus.set")}
                  </Button>
                )}
                {canEdit && (
                  <Button
                    variant="quiet"
                    size="icon-sm"
                    className={cn(!editing && "max-lg:hidden", "lg:opacity-0 lg:group-hover:opacity-100 lg:focus-visible:opacity-100")}
                    aria-label={`${t("roster.remove")}: ${p.first_name} ${p.last_name}`}
                    title={t("roster.remove")}
                    onClick={async () => {
                      if (await confirm({ title: t("roster.removeConfirm", { name: `${p.first_name} ${p.last_name}` }), confirm: t("roster.remove"), danger: true }))
                        remove.mutate(p.id);
                    }}
                  >
                    <Trash2 aria-hidden />
                  </Button>
                )}
                {canEdit && statusFor === p.player_id && teamMembers.data && <AccountLine orgId={orgId} teamId={teamId} entry={p} members={teamMembers.data} rosterKey={key} />}
                {canEdit && statusFor === p.player_id && (
                  <StatusEditor
                    orgId={orgId}
                    teamId={teamId}
                    playerId={p.player_id}
                    name={`${p.first_name} ${p.last_name}`}
                    status={p.status}
                    rosterKey={key}
                    onDone={() => setStatusFor(null)}
                  />
                )}
              </li>
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        )}
      </section>

      {canEdit && inline && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <h3 className="mb-4 font-semibold">{t("roster.addTitle")}</h3>
            {addForm}
          </Card>
          <Card>{csv}</Card>
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
    <div className="space-y-4">
      <h3 className="font-semibold">{t("roster.csvTitle")}</h3>
      <p className="text-sm text-muted">{t("roster.csvHint")}</p>
      <a href={templateHref} download="kader-vorlage.csv" className="inline-block text-sm font-medium text-accent hover:underline">
        {t("roster.csvTemplate")}
      </a>
      <div className="space-y-1">
        <span className="block text-sm font-semibold">{t("roster.csvFile")}</span>
        <label className="flex min-h-10 cursor-pointer items-center gap-3 px-1 text-[0.9375rem] ring-1 ring-inset ring-foreground/20 focus-within:ring-2 focus-within:ring-accent hover:ring-foreground/40">
          <span className="ml-1 bg-surface px-3 py-1 text-sm font-semibold">{t("roster.csvChoose")}</span>
          <span className="min-w-0 truncate text-muted">{file?.name ?? t("roster.csvNone")}</span>
          <input
            type="file"
            accept=".csv,text/csv"
            aria-label={t("roster.csvFile")}
            className="sr-only"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setResult(null);
              setDone(null);
            }}
          />
        </label>
      </div>
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
        <ul className="max-h-40 space-y-1 overflow-auto bg-surface p-3 text-sm" data-testid="csv-preview">
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
    </div>
  );
}

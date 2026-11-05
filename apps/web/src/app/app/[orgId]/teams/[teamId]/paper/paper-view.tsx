"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { cn } from "@/lib/utils";
import { FileField } from "@/components/ui/file-field";

type Upload = Schemas["PaperUploadOut"];
interface PlayerRow {
  number: number;
  name: string | null;
  goals: number;
  misses: number;
  seven_m_goals: number;
  seven_m_misses: number;
  suspensions: number;
  assists: number;
}
interface Extraction {
  date: string | null;
  opponent: string | null;
  score: { own: number; opponent: number } | null;
  halftime: { own: number; opponent: number } | null;
  players: PlayerRow[];
  [key: string]: unknown;
}
const COUNTS = ["goals", "seven_m_goals", "misses", "seven_m_misses", "suspensions", "assists"] as const;
const cell = "w-14 rounded border bg-background px-1 py-0.5 text-right tabular-nums";

/** Review next to the photo (addendum 01, 5.9): the user confirms what the model read. */
function Review({ orgId, upload, onDone }: { orgId: string; upload: Upload; onDone: () => void }) {
  const t = useTranslations("paper");
  const tr = useTranslations();
  const [x, setX] = useState<Extraction>(upload.extraction as unknown as Extraction);
  const [issues, setIssues] = useState(upload.errors);
  const [error, setError] = useState<ErrorKey | null>(null);
  const flagged = (field: string) => issues.some((i) => i.field === field || i.field.startsWith(`${field}.`));
  const path = { org_id: orgId, upload_id: upload.id };
  const check = useMutation({
    mutationFn: async () => {
      const r = await api.PUT("/v1/orgs/{org_id}/paper-photos/{upload_id}", { params: { path }, body: { extraction: { ...x, uncertain: [] } } });
      if (r.error) throw r.error;
      return r.data;
    },
    onSuccess: (u) => setIssues(u.errors),
    onError: (e) => setError(errorKey(e)),
  });
  const confirm = useMutation({
    mutationFn: async (accept: boolean) => {
      await check.mutateAsync();
      const r = await api.POST("/v1/orgs/{org_id}/paper-photos/{upload_id}/confirm", { params: { path }, body: { accept_warnings: accept } });
      if (r.error) throw r.error;
      return r.data;
    },
    onSuccess: onDone,
    onError: (e) => setError(errorKey(e)),
  });
  const setPlayer = (i: number, k: keyof PlayerRow, v: string) =>
    setX((s) => ({ ...s, players: s.players.map((p, j) => (j === i ? { ...p, [k]: k === "name" ? v || null : Number(v) || 0 } : p)) }));
  const score = (key: "score" | "halftime", side: "own" | "opponent", v: string) =>
    setX((s) => ({ ...s, [key]: { own: 0, opponent: 0, ...(s[key] ?? {}), [side]: Number(v) || 0 } }));
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={`/v1/orgs/${orgId}/paper-photos/${upload.id}/photo`} alt={t("photoAlt")} className="w-full rounded-lg ring-1 ring-inset ring-border" />
      <form className="space-y-3 text-sm" onSubmit={(e: FormEvent) => e.preventDefault()} aria-label={t("review")}>
        <div className="flex flex-wrap gap-3">
          <label>
            {t("date")}
            <input className={cn(cell, "ml-1 w-36", flagged("date") && "border-error")} type="date" value={x.date ?? ""} onChange={(e) => setX({ ...x, date: e.target.value })} />
          </label>
          <label>
            {t("opponent")}
            <input className={cn(cell, "ml-1 w-40 text-left", flagged("opponent") && "border-error")} value={x.opponent ?? ""} onChange={(e) => setX({ ...x, opponent: e.target.value })} />
          </label>
        </div>
        <div className="flex flex-wrap gap-3">
          {(["score", "halftime"] as const).map((k) => (
            <fieldset key={k} className={cn("rounded border p-2", flagged(k) ? "border-error" : "border-border")}>
              <legend>{t(k)}</legend>
              <input aria-label={t(`${k}Own`)} className={cell} type="number" min={0} value={x[k]?.own ?? ""} onChange={(e) => score(k, "own", e.target.value)} />
              {" : "}
              <input aria-label={t(`${k}Opp`)} className={cell} type="number" min={0} value={x[k]?.opponent ?? ""} onChange={(e) => score(k, "opponent", e.target.value)} />
            </fieldset>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="text-sm">
            <thead>
              <tr className="text-left text-muted">
                <th className="pr-2 font-normal">{t("number")}</th>
                <th className="pr-2 font-normal">{t("name")}</th>
                {COUNTS.map((c) => (
                  <th key={c} className="pr-2 font-normal">{t(`col_${c}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {x.players.map((p, i) => (
                <tr key={i}>
                  <td className="pr-2 tabular-nums">#{p.number}</td>
                  <td className="pr-2">
                    <input aria-label={t("nameOf", { n: p.number })} className={cn(cell, "w-28 text-left")} value={p.name ?? ""} onChange={(e) => setPlayer(i, "name", e.target.value)} />
                  </td>
                  {COUNTS.map((c) => (
                    <td key={c} className="pr-2">
                      <input
                        aria-label={t("cellOf", { n: p.number, col: t(`col_${c}`) })}
                        type="number"
                        min={0}
                        className={cn(cell, flagged(`players[${i}].${c}`) && "border-error")}
                        value={p[c]}
                        onChange={(e) => setPlayer(i, c, e.target.value)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {issues.length > 0 && (
          <ul className="list-disc space-y-1 pl-5" aria-live="polite">
            {issues.map((i, k) => (
              <li key={k}>{t(`issue_${i.code}`, { field: i.field })}</li>
            ))}
          </ul>
        )}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" onClick={() => check.mutate()}>{t("check")}</Button>
          <Button type="button" disabled={confirm.isPending} onClick={() => confirm.mutate(issues.length > 0)}>
            {issues.length > 0 ? t("confirmAnyway") : t("confirm")}
          </Button>
        </div>
      </form>
    </div>
  );
}

export function PaperView({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("paper");
  const format = useFormatter();
  const tr = useTranslations();
  const tf = useTranslations("file");
  const qc = useQueryClient();
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const [busy, setBusy] = useState(false);
  // "Auslesen" waits for a photo
  const [picked, setPicked] = useState(false);
  const team = { org_id: orgId, team_id: teamId };
  const list = useQuery({
    queryKey: ["paper-photos", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/paper-photos", { params: { path: team } })).data ?? [],
  });
  const upload = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const file = (e.currentTarget.elements.namedItem("photo") as HTMLInputElement).files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    const body = new FormData();
    body.append("file", file);
    const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/paper-photos", {
      params: { path: team },
      body: body as unknown as { file: string },
      bodySerializer: (b) => b as unknown as FormData,
    });
    setBusy(false);
    if (r.error || !r.data) {
      setError(errorKey(r.error));
      return;
    }
    setOpen(r.data.id);
    void qc.invalidateQueries({ queryKey: ["paper-photos", teamId] });
  };
  const items = list.data ?? [];
  const current = items.find((u) => u.id === open);
  return (
    <div className="space-y-4">
      {/* the page title comes from the area header */}
      <p className="max-w-prose text-sm text-muted">{t("photoHint")}</p>
      <form onSubmit={upload} onChange={(e) => setPicked(!!(e.currentTarget.elements.namedItem("photo") as HTMLInputElement | null)?.files?.length)} className="flex flex-wrap items-end gap-3 border-b border-foreground/15 pb-5">
        <label className="text-sm">
          <span className="block font-medium">{t("photo")}</span>
          <FileField name="photo" accept="image/jpeg,image/png,image/webp" capture="environment" required button={tf("choosePhoto")} empty={tf("none")} />
        </label>
        <Button type="submit" disabled={busy || !picked}>{busy ? t("reading") : t("read")}</Button>
      </form>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      {current && current.status === "extracted" && (
        <Review
          key={current.id}
          orgId={orgId}
          upload={current}
          onDone={() => {
            setOpen(null);
            void qc.invalidateQueries({ queryKey: ["paper-photos", teamId] });
          }}
        />
      )}
      <ul className="divide-y divide-foreground/10 text-sm">
        {items.map((u) => (
          <li key={u.id} className="flex min-h-11 flex-wrap items-center gap-x-3 py-1">
            <span className="tabular-nums">{format.dateTime(new Date(u.created_at), { dateStyle: "medium", timeStyle: "short" })}</span>
            <span className="text-muted">{t(`status_${u.status}`)}</span>
            {u.status === "extracted" && (
              <button type="button" className="font-medium underline underline-offset-4" onClick={() => setOpen(u.id)}>{t("review")}</button>
            )}
            {u.match_id && (
              <Link className="font-medium underline underline-offset-4" href={`/app/${orgId}/matches/${u.match_id}`}>{t("toMatch")}</Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

/** Federation overview (addendum 01, 5.10): usage per club, anonymised aggregates, invitations. */
export function FederationView({ id, initial }: { id: string; initial: Schemas["Overview"] }) {
  const t = useTranslations("federation");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const path = { federation_id: id };
  const data = useQuery({
    queryKey: ["federation", id],
    queryFn: async () => (await api.GET("/v1/federations/{federation_id}", { params: { path } })).data ?? initial,
    initialData: initial,
  }).data;
  const invite = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/federations/{federation_id}/invites", { params: { path }, body: { email } });
      if (r.error) throw r.error;
    },
    onSuccess: () => {
      setSent(email);
      setEmail("");
      setError(null);
      void qc.invalidateQueries({ queryKey: ["federation", id] });
    },
    onError: (e) => setError(errorKey(e)),
  });
  const remove = useMutation({
    mutationFn: async (org: string) => api.DELETE("/v1/federations/{federation_id}/members/{org_id}", { params: { path: { ...path, org_id: org } } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["federation", id] }),
  });
  const f = data.federation as { name: string; plan: string; seat_quota: number; contract_until: string | null };
  const agg = data.aggregate as { clubs_with_data: number; min_clubs: number; matches_with_events?: number; goals_per_match?: number | null; shooting_pct?: number | null };
  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <header>
        <h1 className="text-2xl font-semibold">{f.name}</h1>
        <p className="text-sm text-muted">
          {t("quota", { used: data.seats_used, invited: data.open_invites, quota: f.seat_quota })} · {t("plan", { plan: f.plan })}
          {f.contract_until && ` · ${t("until", { date: format.dateTime(new Date(f.contract_until), { dateStyle: "medium" }) })}`}
        </p>
      </header>
      <Card className="space-y-2">
        <h2 className="font-semibold">{t("invite")}</h2>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            invite.mutate();
          }}
        >
          <label className="flex-1">
            <span className="sr-only">{t("email")}</span>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("email")} className="min-h-10 w-full rounded-md border border-border bg-background px-3" />
          </label>
          <Button type="submit" disabled={invite.isPending}>{t("send")}</Button>
        </form>
        {sent && <p className="text-sm text-ok">{t("sent", { email: sent })}</p>}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </Card>
      <section aria-labelledby="members">
        <h2 id="members" className="mb-2 text-lg font-semibold">{t("members")}</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2">{t("club")}</th>
                <th className="py-2">{t("since")}</th>
                <th className="py-2">{t("teams")}</th>
                <th className="py-2">{t("matches")}</th>
                <th className="py-2">{t("people")}</th>
                <th className="py-2">{t("analyses")}</th>
                <th className="py-2"><span className="sr-only">{t("actions")}</span></th>
              </tr>
            </thead>
            <tbody>
              {data.members.map((m) => (
                <tr key={m.organization_id} className="border-b border-border">
                  <td className="py-2">{m.name}</td>
                  <td className="py-2">{format.dateTime(new Date(m.joined_at), { dateStyle: "medium" })}</td>
                  <td className="py-2 tabular-nums">{m.teams}</td>
                  <td className="py-2 tabular-nums">{m.matches}</td>
                  <td className="py-2 tabular-nums">{m.members}</td>
                  <td className="py-2 tabular-nums">{m.analyses_30d}</td>
                  <td className="py-2">
                    <button type="button" className="text-error underline" onClick={() => remove.mutate(m.organization_id)}>
                      {t("remove")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section aria-labelledby="aggregate">
        <h2 id="aggregate" className="mb-2 text-lg font-semibold">{t("aggregate")}</h2>
        {agg.matches_with_events != null ? (
          <dl className="grid grid-cols-3 gap-3">
            <div className="rounded border border-border p-3"><dt className="text-sm text-muted">{t("aggMatches")}</dt><dd className="text-2xl font-semibold">{agg.matches_with_events}</dd></div>
            <div className="rounded border border-border p-3"><dt className="text-sm text-muted">{t("aggGoals")}</dt><dd className="text-2xl font-semibold">{agg.goals_per_match ?? "-"}</dd></div>
            <div className="rounded border border-border p-3"><dt className="text-sm text-muted">{t("aggShooting")}</dt><dd className="text-2xl font-semibold">{agg.shooting_pct != null ? `${Math.round(agg.shooting_pct * 100)} %` : "-"}</dd></div>
          </dl>
        ) : (
          <p className="text-sm text-muted">{t("tooFew", { n: agg.clubs_with_data, min: agg.min_clubs })}</p>
        )}
        <p className="mt-2 text-xs text-muted">{t("privacy")}</p>
      </section>
    </main>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

/** People asking to join a team (players found the team in the official data): each with the
 * squad entry it most likely is, so one click links the account to the right player. */
export function JoinRequests({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("requests");
  const tr = useTranslations();
  const qc = useQueryClient();
  const path = { org_id: orgId, team_id: teamId };
  const [error, setError] = useState<ErrorKey | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ["join-requests", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/join-requests", { params: { path } })).data ?? [],
  });
  const act = useMutation({
    mutationFn: async (v: { id: string; name: string; how: "suggested" | "new" | "decline" }) => {
      const p = { params: { path: { ...path, request_id: v.id } } };
      const r =
        v.how === "decline"
          ? await api.POST("/v1/orgs/{org_id}/teams/{team_id}/join-requests/{request_id}/decline", p)
          : await api.POST("/v1/orgs/{org_id}/teams/{team_id}/join-requests/{request_id}/approve", { ...p, body: v.how === "new" ? { new_entry: true } : null });
      if (r.error) throw r.error;
      return v;
    },
    onSuccess: (v) => {
      setError(null);
      setSaid(v.how === "decline" ? t("declined", { name: v.name }) : t("approved", { name: v.name }));
      void qc.invalidateQueries({ queryKey: ["join-requests", teamId] });
      void qc.invalidateQueries({ queryKey: ["roster"] });
    },
    onError: (e) => setError(errorKey(e)),
  });
  const rows = q.data ?? [];
  return (
    <section className="space-y-3" aria-labelledby="join-requests" data-testid="join-requests">
      {/* the page carries the visible title */}
      <h2 id="join-requests" className="sr-only">
        {t("joinTitle")}
      </h2>
      <div aria-live="polite" className="space-y-2">
        {said && <p className="text-sm text-ok">{said}</p>}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </div>
      {q.isSuccess && rows.length === 0 && <p className="text-sm text-muted">{t("joinNone")}</p>}
      <ul className="divide-y divide-foreground/10 border-t-2 border-foreground">
        {rows.map((r) => {
          const name = `${r.first_name} ${r.last_name}`;
          const s = r.suggested;
          return (
            <li key={r.id} className="space-y-2 py-3" data-testid="join-request">
              <p>
                <span className="font-medium">{t("wantsToJoin", { name })}</span>
                <span className="text-sm text-muted">
                  {` · ${r.email}`}
                  {r.jersey_number != null && ` · #${r.jersey_number}`}
                  {` · ${t(r.role === "goalkeeper" ? "goalkeeper" : "player")}`}
                </span>
              </p>
              {r.message && <p className="border-l-2 border-foreground/20 pl-3 text-sm">{r.message}</p>}
              {/* the squad entry it most likely is: confirming links the account to it */}
              {s && <p className="text-sm">{t("matches", { who: `${s.jersey_number != null ? `#${s.jersey_number} ` : ""}${s.first_name} ${s.last_name}` })}</p>}
              <div className="flex flex-wrap gap-2">
                <Button size="sm" loading={act.isPending && act.variables?.id === r.id} onClick={() => act.mutate({ id: r.id, name, how: "suggested" })}>
                  {s ? t("confirmMatch") : t("admit")}
                </Button>
                {s && (
                  <Button size="sm" variant="secondary" onClick={() => act.mutate({ id: r.id, name, how: "new" })}>
                    {t("admitNew")}
                  </Button>
                )}
                <Button size="sm" variant="quiet" onClick={() => act.mutate({ id: r.id, name, how: "decline" })}>
                  {t("decline")}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** A second person of a club already in the app asks for access (club admins decide). */
export function AccessRequests({ orgId, teams }: { orgId: string; teams: { id: string; name: string }[] }) {
  const t = useTranslations("requests");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ["access-requests", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/access-requests", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  const act = useMutation({
    mutationFn: async (v: { id: string; name: string; how: "coach" | "admin" | "decline" }) => {
      const p = { params: { path: { org_id: orgId, request_id: v.id } } };
      const r =
        v.how === "decline"
          ? await api.POST("/v1/orgs/{org_id}/access-requests/{request_id}/decline", p)
          : await api.POST("/v1/orgs/{org_id}/access-requests/{request_id}/approve", {
              ...p,
              body: v.how === "admin" ? { org_role: "org_admin", team_role: "coach" } : { org_role: "member", team_role: "coach" },
            });
      if (r.error) throw r.error;
      return v;
    },
    onSuccess: (v) => {
      setError(null);
      setSaid(v.how === "decline" ? t("declined", { name: v.name }) : t("approved", { name: v.name }));
      void qc.invalidateQueries({ queryKey: ["access-requests", orgId] });
    },
    onError: (e) => setError(errorKey(e)),
  });
  const rows = (q.data ?? []).filter((r) => r.status === "pending");
  const teamName = (id: string | null) => teams.find((x) => x.id === id)?.name;
  return (
    <div className="space-y-3" id="access-requests" data-testid="access-requests">
      <h3 className="font-semibold">{t("accessTitle")}</h3>
      <div aria-live="polite" className="space-y-2">
        {said && <p className="text-sm text-ok">{said}</p>}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </div>
      {q.isSuccess && rows.length === 0 && <p className="text-sm text-muted">{t("accessNone")}</p>}
      {rows.length > 0 && (
        <ul className="divide-y divide-foreground/10 border-t border-foreground/15">
          {rows.map((r) => (
            <li key={r.id} className="space-y-2 py-3">
              <p>
                <span className="font-medium">{r.name}</span>
                <span className="text-sm text-muted">{` · ${r.email} · ${format.dateTime(new Date(r.created_at), { dateStyle: "medium" })}`}</span>
              </p>
              <p className="text-sm">{teamName(r.team_id) ? t("forTeam", { team: teamName(r.team_id)! }) : r.official_team_id ? t("forNewTeam") : t("forClub")}</p>
              {r.message && <p className="border-l-2 border-foreground/20 pl-3 text-sm">{r.message}</p>}
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={() => act.mutate({ id: r.id, name: r.name, how: "coach" })}>
                  {t("asCoach")}
                </Button>
                <Button size="sm" variant="secondary" onClick={() => act.mutate({ id: r.id, name: r.name, how: "admin" })}>
                  {t("asAdmin")}
                </Button>
                <Button size="sm" variant="quiet" onClick={() => act.mutate({ id: r.id, name: r.name, how: "decline" })}>
                  {t("decline")}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const METHODS = ["mail_domain", "second_official", "federation", "operator"] as const;

/** Whether the club taken over from the official data is confirmed, and the ways to get there.
 * Until then share links and public profiles stay off and opponents stay numbers in reports. */
export function Verification({ orgId }: { orgId: string }) {
  const t = useTranslations("verification");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const [error, setError] = useState<ErrorKey | null>(null);
  const q = useQuery({
    queryKey: ["verification", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/verification", { params: { path: { org_id: orgId } } })).data ?? null,
  });
  const confirm = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/verification/confirm", { params: { path: { org_id: orgId } } });
      if (r.error) throw r.error;
    },
    onSuccess: () => (setError(null), void qc.invalidateQueries({ queryKey: ["verification", orgId] })),
    onError: (e) => setError(errorKey(e)),
  });
  const v = q.data;
  if (!v || v.verification === "none") return null;
  if (v.verification === "verified")
    return (
      <p className="flex items-center gap-2 text-sm" data-testid="verification">
        <BadgeCheck aria-hidden className="size-4" />
        {t("verified", { via: t(`via_${(v.verified_via ?? "operator") as "operator"}`), when: v.verified_at ? format.dateTime(new Date(v.verified_at), { dateStyle: "medium" }) : "" })}
      </p>
    );
  const ways = METHODS.filter((m) => v.methods.length === 0 || v.methods.includes(m));
  return (
    <div className="space-y-3" data-testid="verification">
      <h3 className="font-semibold">{t("title")}</h3>
      <p className="text-sm">{t("why")}</p>
      <ul className="list-disc space-y-1 pl-5 text-sm">
        {ways.map((m) => (
          <li key={m}>{m === "mail_domain" && v.club_domains.length > 0 ? t("way_mail_domain_known", { domains: v.club_domains.join(", ") }) : t(`way_${m}`)}</li>
        ))}
      </ul>
      <Button size="sm" variant="secondary" loading={confirm.isPending} onClick={() => confirm.mutate()}>
        {t("confirm")}
      </Button>
      <div aria-live="polite">{error && <Alert>{tr(`errors.${error}`)}</Alert>}</div>
    </div>
  );
}

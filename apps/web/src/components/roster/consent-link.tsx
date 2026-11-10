"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { control } from "@/components/ui/field";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

/** "Einwilligungen" (SPEC 7.10): one link for the team chat; consent without an account. */
export function ConsentLinkBox({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("consentLink");
  const format = useFormatter();
  const qc = useQueryClient();
  const path = { params: { path: { org_id: orgId, team_id: teamId } } };
  const [url, setUrl] = useState<string | null>(null);
  const link = useQuery({
    queryKey: ["consent-link", teamId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/consent-link", path)).data ?? null,
  });
  const create = useMutation({
    mutationFn: async () => (await api.POST("/v1/orgs/{org_id}/teams/{team_id}/consent-link", path)).data,
    onSuccess: (d) => {
      if (d) setUrl(`${window.location.origin}/einwilligung/${d.token}`);
      void qc.invalidateQueries({ queryKey: ["consent-link", teamId] });
    },
  });
  const revoke = useMutation({
    mutationFn: async () => api.DELETE("/v1/orgs/{org_id}/teams/{team_id}/consent-link", path),
    onSuccess: () => (setUrl(null), void qc.invalidateQueries({ queryKey: ["consent-link", teamId] })),
  });
  const active = link.data;
  return (
    <section aria-labelledby="consent-link-title" className="space-y-2" data-testid="consent-link">
      <h3 id="consent-link-title" className="font-semibold">
        {t("staffTitle")}
      </h3>
      {active && (
        <p className="text-sm text-muted">
          {t("status", { n: active.answers, date: format.dateTime(new Date(active.expires_at), { dateStyle: "medium" }) })}
        </p>
      )}
      {url && <input readOnly value={url} onFocus={(e) => e.currentTarget.select()} className={cn(control, "font-mono text-xs")} data-testid="consent-link-url" />}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" loading={create.isPending} onClick={() => create.mutate()}>
          {active ? t("renew") : t("create")}
        </Button>
        {active && (
          <Button variant="ghost" loading={revoke.isPending} onClick={() => revoke.mutate()}>
            {t("revoke")}
          </Button>
        )}
      </div>
    </section>
  );
}

"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

/** A club admin accepts a federation licence for one of the clubs they administer (5.10). */
export function JoinView({ token, orgs }: { token: string; orgs: { id: string; name: string }[] }) {
  const t = useTranslations("federation");
  const tr = useTranslations();
  const [org, setOrg] = useState(orgs[0]?.id ?? "");
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const accept = async () => {
    const r = await api.POST("/v1/orgs/{org_id}/federation/join", { params: { path: { org_id: org } }, body: { token } });
    if (r.error) setError(errorKey(r.error));
    else setDone(String((r.data as { federation: string }).federation));
  };
  return (
    <main className="mx-auto max-w-lg px-4 py-10">
      <Card className="space-y-3">
        <h1 className="text-xl font-semibold">{t("joinTitle")}</h1>
        <p className="text-sm text-muted">{t("joinHint")}</p>
        {done ? (
          <p>
            {t("joined", { name: done })}{" "}
            <Link className="font-medium text-accent hover:underline" href={`/app/${org}`}>{t("toClub")}</Link>
          </p>
        ) : orgs.length === 0 ? (
          <Alert>{t("noAdmin")}</Alert>
        ) : (
          <>
            <label className="block text-sm">
              <span className="font-medium">{t("club")}</span>
              <select className="mt-1 block min-h-10 w-full rounded-md bg-raised ring-1 ring-inset ring-border px-2" value={org} onChange={(e) => setOrg(e.target.value)}>
                {orgs.map((o) => (
                  <option key={o.id} value={o.id}>{o.name}</option>
                ))}
              </select>
            </label>
            <Button onClick={() => void accept()}>{t("accept")}</Button>
          </>
        )}
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      </Card>
    </main>
  );
}

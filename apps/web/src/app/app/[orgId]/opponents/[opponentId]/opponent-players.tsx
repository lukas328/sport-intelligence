"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Row = Schemas["OpponentPlayerIn"];

/** Opponent players by number; a name only with its public source, never shown publicly (4.9). */
export function OpponentPlayers({ orgId, opponentId }: { orgId: string; opponentId: string }) {
  const t = useTranslations("opponentPlayers");
  const tr = useTranslations();
  const qc = useQueryClient();
  const path = { org_id: orgId, opponent_id: opponentId };
  const key = ["opponent-players", opponentId];
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<ErrorKey | null>(null);
  const q = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/opponents/{opponent_id}/players", { params: { path } })).data ?? [],
  });
  const list: Row[] = rows ?? (q.data ?? []).map((p) => ({ number: p.number, name: p.name, source: p.source, position: p.position }));
  const save = useMutation({
    mutationFn: async () => {
      const body = list.filter((r) => r.number > 0).map((r) => ({ ...r, name: r.name || null, source: r.source || null }));
      const res = await api.PUT("/v1/orgs/{org_id}/opponents/{opponent_id}/players", { params: { path }, body });
      if (res.error) throw res.error;
    },
    onSuccess: () => (setError(null), setRows(null), void qc.invalidateQueries({ queryKey: key })),
    onError: (e) => setError(errorKey(e)),
  });
  const set = (i: number, patch: Partial<Row>) => setRows(list.map((r, n) => (n === i ? { ...r, ...patch } : r)));
  return (
    <Card className="space-y-3">
      <h2 className="font-semibold">{t("title")}</h2>
      <p className="text-sm text-muted">{t("hint")}</p>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      <ul className="space-y-2" data-testid="opponent-players">
        {list.map((r, i) => (
          <li key={i} className="grid gap-2 sm:grid-cols-[5rem_1fr_1fr_auto] sm:items-end">
            <Input label={t("number")} type="number" min={1} max={99} value={r.number || ""} onChange={(e) => set(i, { number: Number(e.target.value) })} />
            <Input label={t("name")} value={r.name ?? ""} maxLength={120} onChange={(e) => set(i, { name: e.target.value })} />
            <Input label={t("source")} value={r.source ?? ""} maxLength={300} placeholder="https://" onChange={(e) => set(i, { source: e.target.value })} />
            <Button variant="ghost" onClick={() => setRows(list.filter((_, n) => n !== i))}>
              {t("remove")}
            </Button>
          </li>
        ))}
      </ul>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={() => setRows([...list, { number: 0, name: null, source: null, position: null }])}>
          {t("add")}
        </Button>
        <Button loading={save.isPending} disabled={rows === null} onClick={() => save.mutate()}>
          {t("save")}
        </Button>
      </div>
    </Card>
  );
}

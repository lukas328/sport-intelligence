"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Status = Schemas["PlayerStatusOut"];

/** "Verletzt bis 22. Nov." in the roster row; nothing for a fit player. */
export function StatusLine({ status }: { status: Status | null | undefined }) {
  const t = useTranslations("playerStatus");
  const format = useFormatter();
  if (!status) return null;
  const until = status.until ? format.dateTime(new Date(`${status.until}T12:00:00`), { day: "numeric", month: "short" }) : null;
  return (
    <span className="font-semibold text-foreground" data-testid="player-status">
      {until ? t(`${status.kind}Until`, { date: until }) : t(`${status.kind}Open`)}
      {status.note && <span className="font-normal text-muted">{` · ${status.note}`}</span>}
    </span>
  );
}

/** Staff set a player injured or absent (until a day, with a short note), or back to fit. */
export function StatusEditor({
  orgId,
  teamId,
  playerId,
  name,
  status,
  onDone,
  rosterKey,
}: {
  orgId: string;
  teamId: string;
  playerId: string;
  name: string;
  status: Status | null | undefined;
  onDone: () => void;
  rosterKey: unknown[];
}) {
  const t = useTranslations();
  const qc = useQueryClient();
  const [error, setError] = useState<ErrorKey | null>(null);
  const path = { org_id: orgId, team_id: teamId, player_id: playerId };
  const save = useMutation({
    mutationFn: async (body: Schemas["PlayerStatusIn"] | null) => {
      const r = body
        ? await api.PUT("/v1/orgs/{org_id}/teams/{team_id}/players/{player_id}/status", { params: { path }, body })
        : await api.DELETE("/v1/orgs/{org_id}/teams/{team_id}/players/{player_id}/status", { params: { path } });
      if (r.error) throw r.error;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: rosterKey });
      onDone();
    },
    onError: (e) => setError(errorKey(e)),
  });
  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const kind = String(f.get("kind"));
    if (kind === "fit") return save.mutate(null);
    save.mutate({
      kind: kind as Schemas["PlayerAvailability"],
      until: String(f.get("until") ?? "") || null,
      note: String(f.get("note") ?? "").trim() || null,
    });
  }
  const today = new Date().toISOString().slice(0, 10);
  return (
    <form onSubmit={submit} className="basis-full space-y-3 border-l-2 border-foreground/20 py-1 pl-4" aria-label={t("playerStatus.formFor", { name })} data-testid="status-form">
      <div className="grid gap-3 sm:grid-cols-3">
        <Select label={t("playerStatus.kind")} name="kind" defaultValue={status?.kind ?? "injured"}>
          <option value="fit">{t("playerStatus.fit")}</option>
          <option value="injured">{t("playerStatus.injured")}</option>
          <option value="absent">{t("playerStatus.absent")}</option>
        </Select>
        <Input label={`${t("playerStatus.until")} (${t("common.optional")})`} name="until" type="date" min={today} defaultValue={status?.until ?? ""} />
        <Input label={`${t("playerStatus.note")} (${t("common.optional")})`} name="note" maxLength={140} defaultValue={status?.note ?? ""} />
      </div>
      {error && <p className="text-sm text-error">{t(`errors.${error}`)}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" loading={save.isPending}>
          {t("playerStatus.save")}
        </Button>
        <Button type="button" size="sm" variant="quiet" onClick={onDone}>
          {t("playerStatus.cancel")}
        </Button>
      </div>
    </form>
  );
}

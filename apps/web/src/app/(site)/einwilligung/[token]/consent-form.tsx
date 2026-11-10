"use client";

import type { Schemas } from "@handball/api-client";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Checkbox, Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey } from "@/lib/errors";

type Page = Schemas["PublicConsentPage"];

export function ConsentForm({ token, data }: { token: string; data: Page }) {
  const t = useTranslations("consentLink");
  const tc = useTranslations("consents");
  const te = useTranslations("errors");
  const [agreed, setAgreed] = useState<string[]>([]);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    const { data: res, error: err } = await api.POST("/v1/consent/{token}", {
      params: { path: { token } },
      body: {
        player_id: String(f.get("player")),
        given_by: String(f.get("given_by")) as "self" | "parent" | "guardian",
        given_by_name: String(f.get("name")),
        agreed: agreed as Page["purposes"],
      },
    });
    setBusy(false);
    if (err || !res) return setError(te(errorKey(err)));
    setError(null);
    setDone(String(res.player ?? ""));
  }

  if (done != null) return <Alert kind="success">{t("thanks", { player: done })}</Alert>;
  return (
    <form onSubmit={submit} className="space-y-5" aria-label={t("form")}>
      <Select label={t("player")} name="player" required>
        {data.players.map((p) => (
          <option key={p.id} value={p.id}>
            {p.label}
          </option>
        ))}
      </Select>
      <Select label={t("whoAmI")} name="given_by" defaultValue={data.youth ? "parent" : "self"}>
        <option value="self">{t("by_self")}</option>
        <option value="parent">{t("by_parent")}</option>
        <option value="guardian">{t("by_guardian")}</option>
      </Select>
      <Input label={t("name")} name="name" required minLength={2} maxLength={160} autoComplete="name" />
      <fieldset className="space-y-3">
        <legend className="mb-1 text-sm font-medium">{t("agree")}</legend>
        {data.purposes.map((k) => (
          <div key={k}>
            <Checkbox
              label={tc(`purpose_${k}` as "purpose_analysis")}
              checked={agreed.includes(k)}
              onChange={(e) => setAgreed((a) => (e.currentTarget.checked ? [...a, k] : a.filter((x) => x !== k)))}
            />
            <p className="ml-6 text-xs text-muted">{tc(`purpose_${k}_help` as "purpose_analysis_help")}</p>
          </div>
        ))}
      </fieldset>
      <p className="text-xs text-muted">{t("note")}</p>
      {error && <Alert>{error}</Alert>}
      <Button type="submit" loading={busy}>
        {t("send")}
      </Button>
    </form>
  );
}

"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/field";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

const chf = (cents: number) => `CHF ${(cents / 100).toFixed(2)}`;

/** Annual subscription by invoice with Swiss QR bill (addendum 01, 4.10). */
export function InvoiceOrder({ orgId, goalkeepers }: { orgId: string; goalkeepers: number }) {
  const t = useTranslations("invoices");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const [plan, setPlan] = useState<"team" | "club">("team");
  const [error, setError] = useState<ErrorKey | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const org = { org_id: orgId };
  const price = useQuery({
    queryKey: ["annual", orgId, plan, goalkeepers],
    queryFn: async () =>
      (await api.GET("/v1/orgs/{org_id}/billing/annual", { params: { path: org, query: { plan, goalkeeper_seats: goalkeepers } } })).data,
  });
  const list = useQuery({
    queryKey: ["invoices", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/billing/invoices", { params: { path: org } })).data ?? [],
  });
  const order = useMutation({
    mutationFn: async (body: Schemas["InvoiceOrder"]) => {
      const r = await api.POST("/v1/orgs/{org_id}/billing/invoices", { params: { path: org }, body });
      if (r.error) throw r.error;
      return r.data;
    },
    onSuccess: (inv) => {
      setError(null);
      setDone(t("ordered", { number: inv?.number ?? "" }));
      void qc.invalidateQueries({ queryKey: ["invoices", orgId] });
      void qc.invalidateQueries({ queryKey: ["billing", orgId] });
    },
    onError: (e) => setError(errorKey(e)),
  });
  const c = price.data?.contact ?? {};

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const v = (k: string) => String(f.get(k) ?? "").trim();
    order.mutate({
      plan,
      goalkeeper_seats: goalkeepers,
      voucher: v("voucher") || null,
      contact: {
        name: v("name"),
        attention: v("attention") || null,
        street: v("street"),
        pcode: v("pcode"),
        city: v("city"),
        country: "CH",
        email: v("email"),
        locale: (v("locale") || "de-CH") as "de-CH",
      },
    });
  }

  return (
    <Card className="space-y-3" data-testid="invoice-order">
      <h3 className="font-semibold">{t("title")}</h3>
      <p className="text-sm text-muted">
        {t("intro", { months: price.data?.months ?? 10, days: price.data?.payment_days ?? 30 })}
      </p>
      {error && <Alert>{tr(`errors.${error}`)}</Alert>}
      {done && (
        <Alert kind="success" data-testid="invoice-ordered">
          {done}
        </Alert>
      )}
      {price.data && (
        <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2" aria-label={t("title")}>
          <Select label={t("plan")} value={plan} onChange={(e) => setPlan(e.target.value as "team")}>
            <option value="team">{tr("billing.plan_team")}</option>
            <option value="club">{tr("billing.plan_club")}</option>
          </Select>
          <p className="self-end text-lg font-semibold tabular-nums" data-testid="annual-price">
            {chf(price.data.net_cents)} {t("perYear")}
            {price.data.vat_rate_percent != null && <span className="ml-1 text-sm font-normal text-muted">{t("plusVat", { rate: price.data.vat_rate_percent })}</span>}
          </p>
          <Input label={t("clubName")} name="name" required defaultValue={c.name ?? ""} maxLength={120} />
          <Input label={t("attention")} name="attention" defaultValue={c.attention ?? ""} maxLength={120} />
          <Input label={t("street")} name="street" required defaultValue={c.street ?? ""} maxLength={70} />
          <div className="grid grid-cols-[6rem_1fr] gap-2">
            <Input label={t("pcode")} name="pcode" required defaultValue={c.pcode ?? ""} maxLength={16} />
            <Input label={t("city")} name="city" required defaultValue={c.city ?? ""} maxLength={35} />
          </div>
          <Input label={t("email")} name="email" type="email" required defaultValue={c.email ?? ""} />
          <Select label={t("language")} name="locale" defaultValue={c.locale ?? "de-CH"}>
            <option value="de-CH">Deutsch</option>
            <option value="fr">Français</option>
            <option value="en">English</option>
          </Select>
          <Input label={t("voucher")} name="voucher" maxLength={40} />
          <div className="self-end">
            <Button type="submit" loading={order.isPending}>
              {t("order")}
            </Button>
          </div>
        </form>
      )}
      {(list.data ?? []).length > 0 && (
        <table className="w-full text-sm" data-testid="invoice-list">
          <caption className="sr-only">{t("list")}</caption>
          <thead>
            <tr className="text-left text-muted">
              <th scope="col" className="font-medium">{t("number")}</th>
              <th scope="col" className="font-medium">{t("due")}</th>
              <th scope="col" className="text-right font-medium">{t("amount")}</th>
              <th scope="col" className="font-medium">{t("state")}</th>
            </tr>
          </thead>
          <tbody>
            {(list.data ?? []).map((i) => (
              <tr key={i.id} className="border-t border-border/70">
                <td>
                  <a className="font-medium text-accent hover:underline" href={`/v1/orgs/${orgId}/billing/invoices/${i.id}/pdf`}>
                    {i.number}
                  </a>
                </td>
                <td>{format.dateTime(new Date(i.due_date), { dateStyle: "medium" })}</td>
                <td className="text-right tabular-nums">{chf(i.amount_cents)}</td>
                <td>{i.paid_at ? t("paid") : i.dunning_level >= 2 ? t("dunned") : i.dunning_level === 1 ? t("reminded") : t("open")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

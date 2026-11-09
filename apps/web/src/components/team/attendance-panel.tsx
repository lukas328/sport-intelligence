"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { control } from "@/components/ui/field";
import { api } from "@/lib/client";

type Status = NonNullable<Schemas["AttendanceRecord"]["status"]>;
const STATUSES: Status[] = ["present", "late", "excused", "injured", "absent"];

/** Who replied to a training unit or a match, and who was there (staff). */
export function AttendancePanel({ orgId, kind, id }: { orgId: string; kind: "session" | "match"; id: string }) {
  const t = useTranslations("training");
  const qc = useQueryClient();
  const path = { org_id: orgId, kind, target_id: id };
  const rows = useQuery({
    queryKey: ["attendance", kind, id],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/attendance/{kind}/{target_id}", { params: { path } })).data ?? [],
  });
  const save = useMutation({
    mutationFn: async (rec: Schemas["AttendanceRecord"]) =>
      api.PUT("/v1/orgs/{org_id}/attendance/{kind}/{target_id}", { params: { path }, body: { records: [rec] } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["attendance", kind, id] }),
  });
  const list = rows.data ?? [];
  const yes = list.filter((r) => r.response === "yes").length;
  const no = list.filter((r) => r.response === "no").length;
  return (
    <div className="space-y-2">
      <p className="text-sm text-muted">{t("replies", { yes, no, open: list.length - yes - no })}</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted">
            <th className="py-1 font-normal">{t("player")}</th>
            <th className="py-1 font-normal">{t("reply")}</th>
            <th className="py-1 font-normal">{t("status")}</th>
          </tr>
        </thead>
        <tbody>
          {list.map((r) => (
            <tr key={r.player_id} className="border-t border-border/70">
              <td className="py-1">{r.number != null ? `#${r.number} ` : ""}{r.name}</td>
              <td className="py-1">{r.response ? t(`reply_${r.response}`) : "-"}</td>
              <td className="py-1">
                <select
                  aria-label={t("statusFor", { name: r.name })}
                  className={control}
                  value={r.status ?? ""}
                  onChange={(e) => save.mutate({ player_id: r.player_id, status: (e.target.value || null) as Status | null })}
                >
                  <option value="">-</option>
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>{t(`status_${s}`)}</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

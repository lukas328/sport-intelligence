"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/card";
import { useConfirm } from "@/components/ui/confirm";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";
import { canGive, type PersonRole } from "@/lib/roles";

const GIVEN: PersonRole[] = ["trainer", "co_trainer", "player"];

/**
 * The people of one team with one of the four roles each (finding K18): Trainer, Co-Trainer,
 * Spieler, Eltern. A Trainer or Co-Trainer changes it in place; making or unmaking a Trainer (club
 * admin) is for club admins. Parents keep their role (they come with their child).
 */
export function TeamPeople({ orgId, teamId, isAdmin, meId }: { orgId: string; teamId: string; isAdmin: boolean; meId: string | null }) {
  const t = useTranslations();
  const tp = useTranslations("people");
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [error, setError] = useState<ErrorKey | null>(null);
  const key = ["team-members", teamId];
  const path = { org_id: orgId, team_id: teamId };
  const members = useQuery({
    queryKey: key,
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/teams/{team_id}/members", { params: { path } })).data ?? [],
  });
  const setRole = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: PersonRole }) => {
      const r = await api.PUT("/v1/orgs/{org_id}/teams/{team_id}/members/{user_id}/person-role", {
        params: { path: { ...path, user_id: userId } },
        body: { role },
      });
      if (r.error) throw r.error;
    },
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: key });
      void qc.invalidateQueries({ queryKey: ["members", orgId] });
    },
    onError: (e) => setError(errorKey(e)),
  });
  const remove = useMutation({
    mutationFn: async (userId: string) => {
      const r = await api.DELETE("/v1/orgs/{org_id}/teams/{team_id}/members/{user_id}", { params: { path: { ...path, user_id: userId } } });
      if (r.error) throw r.error;
    },
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: key });
    },
    onError: (e) => setError(errorKey(e)),
  });
  const rows = members.data ?? [];
  if (members.isSuccess && rows.length === 0) return <p className="m-0 text-[15px] text-ink-2">{tp("nobody")}</p>;
  return (
    <div className="space-y-2">
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      <ul className="m-0 list-none divide-y divide-rule p-0" data-testid="team-people">
        {rows.map((m) => {
          const role = (m.person_role ?? null) as PersonRole | null;
          const self = m.user_id === meId;
          // a Co-Trainer does not change a Trainer, nobody changes a parent here, nobody themself
          const editable = role !== null && role !== "parent" && !self && (isAdmin || role !== "trainer");
          return (
            <li key={m.user_id} className="flex min-h-14 flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2">
              <span className="min-w-0">
                <span className="block font-bold">{m.name}</span>
                <span className="block truncate text-[15px] text-ink-2">{m.email}</span>
              </span>
              <span className="flex flex-wrap items-center gap-3">
                {editable ? (
                  <label className="flex items-center gap-2 text-[15px]">
                    <span className="sr-only">{tp("roleOf", { name: m.name })}</span>
                    <select
                      value={role ?? ""}
                      disabled={setRole.isPending}
                      onChange={(e) => setRole.mutate({ userId: m.user_id, role: e.target.value as PersonRole })}
                      className="min-h-11 border-2 border-ink bg-transparent px-2 text-[15px]"
                      data-testid="person-role"
                    >
                      {GIVEN.filter((r) => canGive(isAdmin ? "org_admin" : "member", r) || r === role).map((r) => (
                        <option key={r} value={r}>
                          {t(`personRoles.${r}`)}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <span className="text-[15px] text-ink-2">{role ? t(`personRoles.${role}`) : t("personRoles.guest")}</span>
                )}
                {editable && (
                  <button
                    type="button"
                    className="min-h-11 cursor-pointer text-[15px] text-ink-2 underline decoration-[1.5px] underline-offset-4"
                    onClick={async () => {
                      if (await confirm({ title: tp("removeTitle", { name: m.name }), body: tp("removeBody"), confirm: tp("remove") })) remove.mutate(m.user_id);
                    }}
                  >
                    {tp("remove")}
                  </button>
                )}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

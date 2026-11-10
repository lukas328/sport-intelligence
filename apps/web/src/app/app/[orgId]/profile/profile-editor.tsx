"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

type Mine = Schemas["MyProfile"];

function Editor({ orgId, item }: { orgId: string; item: Mine }) {
  const t = useTranslations("profile");
  const tr = useTranslations();
  const format = useFormatter();
  const qc = useQueryClient();
  const p = item.profile;
  const [error, setError] = useState<ErrorKey | null>(null);
  const path = { org_id: orgId, player_id: item.player_id };
  const save = useMutation({
    mutationFn: async (body: Schemas["ProfileIn"]) => {
      const r = await api.PUT("/v1/orgs/{org_id}/players/{player_id}/profile", { params: { path }, body });
      if (r.error) throw r.error;
    },
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ["my-profiles", orgId] });
    },
    onError: (e) => setError(errorKey(e)),
  });
  const remove = useMutation({
    mutationFn: async () => api.DELETE("/v1/orgs/{org_id}/players/{player_id}/profile", { params: { path } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["my-profiles", orgId] }),
  });
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    save.mutate({
      active: f.get("active") === "on",
      bio: String(f.get("bio") || "") || null,
      stats: f.getAll("stats").map(String),
      reel_ids: f.getAll("reels").map(String),
      show_position: f.get("show_position") === "on",
      show_hand: f.get("show_hand") === "on",
      indexable: f.get("indexable") === "on",
    });
  };
  const url = p ? `${typeof window === "undefined" ? "" : window.location.origin}/p/${p.slug}` : null;
  return (
    <section className="space-y-3 border-t-2 border-foreground pt-4">
      <h2 className="text-lg font-semibold">
        {item.name}
        {item.relation === "guardian" && <span className="text-sm font-normal text-muted"> {t("child")}</span>}
      </h2>
      {/* a missing consent is a step to take, not an error; the form waits until then */}
      {item.blocked && (
        <p className="text-[0.9375rem]">
          {t(`blocked_${item.blocked}`)}{" "}
          {item.blocked === "consent-missing" && (
            <Link href={`/app/${orgId}/consents`} className="font-semibold underline underline-offset-4">
              {t("toConsents")}
            </Link>
          )}
        </p>
      )}
      {!item.blocked && <form onSubmit={submit} className="space-y-3" aria-label={t("formFor", { name: item.name })}>
        <label className="flex items-center gap-2 font-medium">
          <input type="checkbox" name="active" defaultChecked={p?.active ?? false} disabled={!!item.blocked} />
          {t("active")}
        </label>
        <label className="block text-sm">
          <span className="font-medium">{t("bio")}</span>
          <textarea name="bio" maxLength={400} rows={3} defaultValue={p?.bio ?? ""} className="mt-1 w-full rounded-md bg-raised ring-1 ring-inset ring-border p-2" />
        </label>
        <fieldset className="text-sm">
          <legend className="font-medium">{t("stats")}</legend>
          <div className="flex flex-wrap gap-3">
            {item.stats_available.map((s) => (
              <label key={s} className="flex items-center gap-1">
                <input type="checkbox" name="stats" value={s} defaultChecked={p?.stats.includes(s) ?? ["goals", "shooting_pct"].includes(s)} />
                {t(`stat_${s}`)}
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset className="text-sm">
          <legend className="font-medium">{t("highlights")}</legend>
          {item.reels.length === 0 ? (
            <p className="text-muted">{t("noReels")}</p>
          ) : (
            item.reels.map((r) => (
              <label key={r.id} className="flex items-center gap-2">
                <input type="checkbox" name="reels" value={r.id} defaultChecked={p?.reel_ids.includes(r.id) ?? false} />
                {format.dateTime(new Date(r.created_at), { dateStyle: "medium" })} ({r.format})
              </label>
            ))
          )}
        </fieldset>
        <div className="flex flex-wrap gap-4 text-sm">
          <label className="flex items-center gap-1">
            <input type="checkbox" name="show_position" defaultChecked={p?.show_position ?? true} />
            {t("showPosition")}
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" name="show_hand" defaultChecked={p?.show_hand ?? true} />
            {t("showHand")}
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" name="indexable" defaultChecked={p?.indexable ?? false} />
            {t("indexable")}
          </label>
        </div>
        {error && <Alert>{tr(`errors.${error}`)}</Alert>}
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={save.isPending}>{t("save")}</Button>
          {p && (
            <button type="button" className="text-sm text-error underline" onClick={() => remove.mutate()}>
              {t("delete")}
            </button>
          )}
        </div>
      </form>}
      {p?.active && url && (
        <p className="text-sm">
          {t("link")}{" "}
          <a className="break-all font-medium text-accent hover:underline" href={url}>{url}</a> · {t("views", { n: p.views })}
        </p>
      )}
    </section>
  );
}

export function ProfileEditor({ orgId }: { orgId: string }) {
  const t = useTranslations("profile");
  const items = useQuery({
    queryKey: ["my-profiles", orgId],
    queryFn: async () => (await api.GET("/v1/orgs/{org_id}/me/profiles", { params: { path: { org_id: orgId } } })).data ?? [],
  });
  // part of "Ich": only for people with a player entry in the squad
  if ((items.data ?? []).length === 0) return null;
  return (
    <section aria-labelledby="player-profile" className="space-y-4">
      <div>
        <h2 id="player-profile" className="text-lg font-semibold">{t("title")}</h2>
        <p className="text-sm text-muted">{t("hint")}</p>
      </div>
      {(items.data ?? []).map((i) => (
        <Editor key={i.player_id} orgId={orgId} item={i} />
      ))}
    </section>
  );
}

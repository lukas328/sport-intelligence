"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { api } from "@/lib/client";

export function NewPlaylist({ orgId, teamId }: { orgId: string; teamId: string }) {
  const t = useTranslations("playlists");
  const router = useRouter();
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const title = String(new FormData(e.currentTarget).get("title"));
    const { data } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/playlists", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: { title },
    });
    if (data) router.push(`/app/${orgId}/playlists/${data.id}`);
  }
  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-2" aria-label={t("new")}>
      <Input label={t("name")} name="title" required maxLength={120} />
      <Button type="submit">{t("new")}</Button>
    </form>
  );
}

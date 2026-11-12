"use client";

import type { Schemas } from "@handball/api-client";
import { useRouter } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/client";

type Link = Schemas["ShareOut"];

/**
 * Teilen (SPEC 7.7, UX test B17): «Link teilen» makes the link (30 days) and copies it in one
 * step; afterwards the side shows the link, «Link kopieren», how often it was opened and «Link
 * sperren».
 */
export function ShareBox({ orgId, teamId, collectionId, link }: { orgId: string; teamId: string; collectionId: string; link: Link | null }) {
  const t = useTranslations("collections");
  const format = useFormatter();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState<string | null>(null);
  const url = (token: string) => `${window.location.origin}/s/${token}`;
  async function copy(token: string) {
    try {
      await navigator.clipboard.writeText(url(token));
      setSaid(t("copied"));
    } catch {
      setSaid(url(token));
    }
  }
  async function share() {
    setBusy(true);
    const { data } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/share-links", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: { kind: "collection", target_id: collectionId, days: 30 },
    });
    // a shared collection is no draft any more
    await api.PATCH("/v1/orgs/{org_id}/collections/{collection_id}", { params: { path: { org_id: orgId, collection_id: collectionId } }, body: { draft: false } });
    setBusy(false);
    if (data) await copy(data.token);
    router.refresh();
  }
  async function revoke() {
    if (!link) return;
    setBusy(true);
    await api.DELETE("/v1/orgs/{org_id}/share-links/{link_id}", { params: { path: { org_id: orgId, link_id: link.id } } });
    setBusy(false);
    setSaid(t("revoked"));
    router.refresh();
  }
  return (
    <div data-testid="share-box">
      <SectionHead as="h2" title={t("shareTitle")} />
      {link ? (
        <>
          <p className="m-0 flex items-baseline gap-3">
            <b className="font-num text-[64px] leading-[.8]" data-testid="share-views">
              {link.views}
            </b>
            <span className="text-[15px] text-ink-2">{t("openedTimes", { n: link.views })}</span>
          </p>
          <p className="mt-2 text-[15px] text-ink-2">{t("validUntil", { date: format.dateTime(new Date(link.expires_at), { day: "numeric", month: "long" }) })}</p>
          {link.token ? (
            <input readOnly value={url(link.token)} onFocus={(e) => e.currentTarget.select()} aria-label={t("linkLabel")} className="mt-3 w-full border-[1.5px] border-ink bg-transparent px-2 py-2 font-mono text-xs" data-testid="share-url" />
          ) : (
            <p className="mt-3 text-[13px] text-ink-2">{t("oldLink")}</p>
          )}
          <div className="mt-3 flex flex-wrap gap-2.5">
            {link.token && (
              <Button size="sm" onClick={() => void copy(link.token!)} data-testid="share-copy">
                {t("copyLink")}
              </Button>
            )}
            <Button size="sm" variant="secondary" loading={busy} onClick={() => void revoke()} data-testid="share-revoke">
              {t("revokeLink")}
            </Button>
          </div>
        </>
      ) : (
        <>
          <p className="text-[15px] text-ink-2">{t("notShared")}</p>
          <Button className="mt-2" loading={busy} onClick={() => void share()} data-testid="share-create">
            {t("shareLink")}
          </Button>
        </>
      )}
      <p role="status" className="mt-2 text-[13px] break-all text-ink-2">
        {said}
      </p>
    </div>
  );
}

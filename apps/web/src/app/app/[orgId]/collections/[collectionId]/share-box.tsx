"use client";

import type { Schemas } from "@handball/api-client";
import { useRouter } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { ShareActions } from "@/components/sharing/share-button";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { reasonFromProblem, type ShareReason } from "@/lib/share/policy";
import { chatText, shareUrl, type T } from "@/lib/share/text";

type Link = Schemas["ShareOut"];

/**
 * Teilen (SPEC 7.7, UX test B17, K20): «Link teilen» makes the link (30 days); afterwards the side
 * shows the link, the ways into the chat (share sheet, WhatsApp with the text, copy), how often
 * it was opened and «Link sperren». Where the team may not share it, it says why.
 */
export function ShareBox({
  orgId,
  teamId,
  collectionId,
  link,
  title,
  scenes,
  blocked = null,
}: {
  orgId: string;
  teamId: string;
  collectionId: string;
  link: Link | null;
  title: string;
  scenes: number;
  blocked?: ShareReason | null;
}) {
  const t = useTranslations("collections");
  const ts = useTranslations("share");
  const root = useTranslations() as unknown as T;
  const format = useFormatter();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState<string | null>(null);
  const [refused, setRefused] = useState<ShareReason | null>(null);
  const reason = blocked ?? refused;
  // the absolute link once the page runs in the browser (the server does not know the host)
  const [origin, setOrigin] = useState("");
  useEffect(() => setOrigin(window.location.origin), []);
  async function share() {
    setBusy(true);
    const { data, error } = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/share-links", {
      params: { path: { org_id: orgId, team_id: teamId } },
      body: { kind: "collection", target_id: collectionId, days: 30 },
    });
    if (data) {
      // a shared collection is no draft any more
      await api.PATCH("/v1/orgs/{org_id}/collections/{collection_id}", { params: { path: { org_id: orgId, collection_id: collectionId } }, body: { draft: false } });
      setSaid(null);
    } else setRefused(reasonFromProblem(error) ?? "forbidden");
    setBusy(false);
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
  const url = link?.token ? shareUrl(origin, link.token) : null;
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
          {url ? (
            <>
              <input readOnly value={url} onFocus={(e) => e.currentTarget.select()} aria-label={t("linkLabel")} className="mt-3 w-full border-[1.5px] border-ink bg-transparent px-2 py-2 font-mono text-xs" data-testid="share-url" />
              <div className="mt-3">
                <ShareActions url={url} text={chatText(root, { kind: "collection", title, scenes })} compact />
              </div>
            </>
          ) : (
            <p className="mt-3 text-[15px] text-ink-2">{t("oldLink")}</p>
          )}
          <Button className="mt-2" size="sm" variant="quiet" loading={busy} onClick={() => void revoke()} data-testid="share-revoke">
            {t("revokeLink")}
          </Button>
        </>
      ) : reason ? (
        <Alert kind="info" data-testid="share-blocked">
          {ts(`reason.${reason}`)}
        </Alert>
      ) : (
        <>
          <p className="text-[15px] text-ink-2">{t("notShared")}</p>
          <Button className="mt-2" loading={busy} onClick={() => void share()} data-testid="share-create">
            {t("shareLink")}
          </Button>
        </>
      )}
      <p role="status" className="mt-2 text-[15px] break-all text-ink-2">
        {said}
      </p>
    </div>
  );
}

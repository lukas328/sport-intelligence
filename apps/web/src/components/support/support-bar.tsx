"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { helpUrl } from "./help-map";

declare global {
  interface Window {
    $crisp?: unknown[];
    CRISP_WEBSITE_ID?: string;
    CRISP_TOKEN_ID?: string;
  }
}

/** Help link for the current screen, support chat (loaded only on click) and feedback (4.11). */
export function SupportBar({ orgId }: { orgId: string }) {
  const t = useTranslations("support");
  const locale = useLocale();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const cfg = useQuery({ queryKey: ["support-config"], queryFn: async () => (await api.GET("/v1/support/config")).data ?? null, staleTime: 3_600_000 });

  function chat() {
    const c = cfg.data?.chat;
    if (!c || c.provider !== "crisp") return;
    // third-party script only after an explicit click (no tracking before)
    window.$crisp = [];
    window.CRISP_WEBSITE_ID = String(c.website_id);
    if (c.token_id) window.CRISP_TOKEN_ID = String(c.token_id);
    const s = document.createElement("script");
    s.src = "https://client.crisp.chat/l.js";
    s.async = true;
    document.head.appendChild(s);
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const file = f.get("shot");
    let screenshot: string | null = null;
    if (file instanceof File && file.size > 0) {
      screenshot = await new Promise<string>((res) => {
        const r = new FileReader();
        r.onload = () => res(String(r.result));
        r.readAsDataURL(file);
      });
    }
    setBusy(true);
    const match = /\/matches\/([0-9a-f-]{36})/.exec(path)?.[1] ?? null;
    const r = await api.POST("/v1/orgs/{org_id}/feedback", {
      params: { path: { org_id: orgId } },
      body: { message: String(f.get("message")), page: path, match_id: match, browser: navigator.userAgent.slice(0, 300), screenshot },
    });
    setBusy(false);
    setError(Boolean(r.error));
    setSent(!r.error);
  }

  return (
    <>
      <a
        href={helpUrl(cfg.data?.help_url ?? "https://handball-ai.ch/hilfe", locale, path)}
        target="_blank"
        rel="noreferrer"
        className="rounded px-3 py-2 hover:bg-surface"
        data-testid="help-link"
      >
        {t("help")}
      </a>
      <button
        type="button"
        className="rounded px-3 py-2 hover:bg-surface"
        onClick={() => {
          setOpen(true);
          setSent(false);
          dialog.current?.showModal();
        }}
      >
        {t("feedback")}
      </button>
      <dialog ref={dialog} className="w-full max-w-md rounded-lg border border-border bg-background p-4 text-foreground backdrop:bg-black/40" onClose={() => setOpen(false)} aria-labelledby="feedback-title">
        {open && (
          <form onSubmit={submit} className="space-y-3">
            <h2 id="feedback-title" className="text-lg font-semibold">
              {t("feedbackTitle")}
            </h2>
            <p className="text-sm text-muted">{t("feedbackIntro")}</p>
            {sent ? (
              <Alert kind="success">{t("thanks")}</Alert>
            ) : (
              <>
                {error && <Alert>{t("failed")}</Alert>}
                <label className="block text-sm font-medium" htmlFor="feedback-message">
                  {t("message")}
                </label>
                <textarea id="feedback-message" name="message" required minLength={3} maxLength={4000} rows={4} className="w-full rounded-md border border-border bg-background p-2" />
                <label className="block text-sm">
                  {t("screenshot")}
                  <input name="shot" type="file" accept="image/png" className="mt-1 block" />
                </label>
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" loading={busy}>
                    {t("send")}
                  </Button>
                  {cfg.data?.chat && (
                    <Button type="button" variant="secondary" onClick={chat}>
                      {t("chat")}
                    </Button>
                  )}
                </div>
              </>
            )}
            <div className="text-right">
              <Button type="button" variant="ghost" onClick={() => dialog.current?.close()}>
                {t("close")}
              </Button>
            </div>
          </form>
        )}
      </dialog>
    </>
  );
}

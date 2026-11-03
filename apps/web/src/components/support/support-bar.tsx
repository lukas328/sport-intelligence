"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { control } from "@/components/ui/field";
import { api } from "@/lib/client";
import { cn } from "@/lib/utils";

declare global {
  interface Window {
    $crisp?: unknown[];
    CRISP_WEBSITE_ID?: string;
    CRISP_TOKEN_ID?: string;
  }
}

type Chat = { provider?: string; website_id?: unknown; token_id?: unknown } | null;

/** Feedback with page, match and browser attached; support chat loaded only on click (4.11). */
export function FeedbackDialog({ orgId, open, onOpenChange, chat }: { orgId: string; open: boolean; onOpenChange: (o: boolean) => void; chat: Chat }) {
  const t = useTranslations("support");
  const path = usePathname();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  function openChat() {
    if (!chat || chat.provider !== "crisp") return;
    // third-party script only after an explicit click (no tracking before)
    window.$crisp = [];
    window.CRISP_WEBSITE_ID = String(chat.website_id);
    if (chat.token_id) window.CRISP_TOKEN_ID = String(chat.token_id);
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
    <Dialog
      open={open}
      onOpenChange={(o) => {
        onOpenChange(o);
        if (o) setSent(false);
      }}
      title={t("feedbackTitle")}
      description={t("feedbackIntro")}
    >
      {sent ? (
        <Alert kind="success">{t("thanks")}</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {error && <Alert>{t("failed")}</Alert>}
          <div className="space-y-1">
            <label className="block text-[0.8125rem] font-medium" htmlFor="feedback-message">
              {t("message")}
            </label>
            <textarea id="feedback-message" name="message" required minLength={3} maxLength={4000} rows={4} className={cn(control, "min-h-24")} />
          </div>
          <label className="block text-[0.8125rem] font-medium">
            {t("screenshot")}
            <input name="shot" type="file" accept="image/png" className="mt-1 block text-sm text-muted file:mr-3 file:rounded-md file:border-0 file:bg-surface file:px-3 file:py-1.5 file:text-foreground" />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" loading={busy}>
              {t("send")}
            </Button>
            {chat && (
              <Button type="button" variant="secondary" onClick={openChat}>
                {t("chat")}
              </Button>
            )}
          </div>
        </form>
      )}
    </Dialog>
  );
}

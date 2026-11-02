"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { api } from "@/lib/client";
import { errorKey, type ErrorKey } from "@/lib/errors";

export function AcceptButton({ token }: { token: string }) {
  const t = useTranslations();
  const router = useRouter();
  const [error, setError] = useState<ErrorKey | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <div className="space-y-3">
      {error && <Alert>{t(`errors.${error}`)}</Alert>}
      <Button
        loading={busy}
        className="w-full"
        onClick={async () => {
          setBusy(true);
          const { data, error } = await api.POST("/v1/invitations/{token}/accept", { params: { path: { token } } });
          setBusy(false);
          if (error) return setError(errorKey(error));
          router.push(`/app/${data.organization_id}`);
          router.refresh();
        }}
      >
        {t("invite.accept")}
      </Button>
    </div>
  );
}

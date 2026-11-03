"use client";

import { RotateCcw, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/card";

export default function AppError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations();
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <EmptyState
      icon={<TriangleAlert />}
      title={t("errors.pageTitle")}
      action={
        <Button variant="secondary" onClick={reset}>
          <RotateCcw aria-hidden />
          {t("common.retry")}
        </Button>
      }
    >
      {t("errors.pageBody")}
    </EmptyState>
  );
}

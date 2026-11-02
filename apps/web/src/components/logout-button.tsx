"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { api } from "@/lib/client";

export function LogoutButton() {
  const t = useTranslations("common");
  const router = useRouter();
  return (
    <button
      type="button"
      className="rounded px-3 py-2 hover:bg-surface"
      onClick={async () => {
        await api.POST("/v1/auth/logout");
        router.push("/login");
        router.refresh();
      }}
    >
      {t("logout")}
    </button>
  );
}

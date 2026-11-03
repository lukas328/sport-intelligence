import type { Metadata } from "next";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";

export const metadata: Metadata = { title: "Verband", robots: { index: false } };

export default async function FederationsPage() {
  const t = await getTranslations("federation");
  const { data } = await (await serverApi()).GET("/v1/federations");
  const list = data ?? [];
  return (
    <main className="mx-auto max-w-4xl space-y-4 px-4 py-8">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      {list.length === 0 ? (
        <EmptyState title={t("none")} />
      ) : (
        <ul className="space-y-2">
          {list.map((f) => (
            <li key={f.id}>
              <Link className="text-accent underline" href={`/federation/${f.id}`}>{f.name}</Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

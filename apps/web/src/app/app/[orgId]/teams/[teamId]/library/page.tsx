import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Film, ListVideo, Presentation, ScanSearch } from "lucide-react";
import { getTranslations } from "next-intl/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("library"))("title") };
}

export default async function LibraryPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  const t = await getTranslations("library");
  const base = `/app/${orgId}/teams/${teamId}`;
  const tiles = [
    { key: "playlists", href: `${base}/playlists`, Icon: ListVideo },
    { key: "plays", href: `${base}/plays`, Icon: Film },
    { key: "presentations", href: `${base}/presentations`, Icon: Presentation },
    { key: "search", href: `${base}/search`, Icon: ScanSearch },
  ] as const;
  return (
    <div className="space-y-6">
      <p className="max-w-2xl text-muted">{t("intro")}</p>
      <ul className="grid gap-4 sm:grid-cols-2">
        {tiles.map(({ key, href, Icon }) => (
          <li key={key}>
            <Link href={href} className="group flex h-full items-start gap-4 rounded-2xl bg-raised p-6 ring-1 ring-border/70 transition-[box-shadow,transform] hover:-translate-y-0.5 hover:shadow-md">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent">
                <Icon aria-hidden className="size-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2 text-lg font-semibold font-wide">
                  {t(key)}
                  <ArrowRight aria-hidden className="size-4 text-muted transition-transform group-hover:translate-x-0.5" />
                </span>
                <span className="mt-1 block text-sm text-muted">{t(`${key}Hint`)}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

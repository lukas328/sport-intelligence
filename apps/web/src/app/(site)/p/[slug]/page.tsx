import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { EmptyState } from "@/components/ui/card";
import { serverApi } from "@/lib/api";

type Params = { params: Promise<{ slug: string }> };

async function load(slug: string) {
  return (await (await serverApi()).GET("/v1/public/profiles/{slug}", { params: { path: { slug } } })).data;
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const data = await load((await params).slug);
  // not indexed unless the player switched it on (5.8)
  return {
    title: data ? `${data.name} · ${data.club}` : "Profil",
    robots: data?.indexable ? { index: true, follow: true } : { index: false, follow: false },
  };
}

/** Public player profile (addendum 01, 5.8). */
export default async function ProfilePage({ params }: Params) {
  const { slug } = await params;
  const t = await getTranslations("profile");
  const tp = await getTranslations();
  const data = await load(slug);
  if (!data) return <EmptyState title={t("invalid")} />;
  const fmt = (k: string, v: number | null | undefined) =>
    v == null ? "-" : k === "shooting_pct" ? `${Math.round(v * 100)} %` : String(v);
  return (
    <main className="mx-auto max-w-2xl space-y-6 px-4 py-10">
      <header className="space-y-1">
        <h1 className="text-3xl font-bold">{data.name}</h1>
        <p className="text-muted">
          {data.team} · {data.club}
        </p>
        <p className="text-sm">
          {data.position && <span>{tp(`positions.${data.position}`)}</span>}
          {data.position && data.shooting_hand && " · "}
          {data.shooting_hand && <span>{tp("profile.hand", { hand: tp(`hands.${data.shooting_hand}`) })}</span>}
        </p>
      </header>
      {data.bio && <p className="whitespace-pre-line">{data.bio}</p>}
      {Object.keys(data.stats).length > 0 && (
        <section aria-labelledby="stats">
          <h2 id="stats" className="mb-2 text-lg font-semibold">{t("season")}</h2>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Object.entries(data.stats).map(([k, v]) => (
              <div key={k} className="rounded-lg bg-raised border border-border p-3">
                <dt className="text-sm text-muted">{t(`stat_${k}`)}</dt>
                <dd className="text-2xl font-semibold tabular-nums">{fmt(k, v)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      {data.reels.length > 0 && (
        <section aria-labelledby="reels" className="space-y-3">
          <h2 id="reels" className="text-lg font-semibold">{t("highlights")}</h2>
          {data.reels.map((id) => (
            <video key={id} controls preload="metadata" className="w-full rounded-lg bg-black" src={`/v1/public/profiles/${slug}/reels/${id}`}>
              <track kind="captions" />
            </video>
          ))}
        </section>
      )}
      <footer className="text-xs text-muted">{t("footer")}</footer>
    </main>
  );
}

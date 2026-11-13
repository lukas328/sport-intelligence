import type { Metadata } from "next";
import { DRILLS, type Focus, type Lang } from "@handball/tactics";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { AreaOrPageHeader } from "@/components/shell/section-nav";
import { DrillCourt } from "@/components/domain/drill-court";
import { cn } from "@/lib/utils";
import { ClubDrills } from "./club-drills";

const FOCI: Focus[] = ["finishing", "wings", "back_court", "pivot", "seven_m", "goalkeeping", "passing", "transition_defence", "fast_break", "defence", "powerplay"];

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("drills"))("title") };
}

export default async function DrillsPage({ params, searchParams }: { params: Promise<{ orgId: string }>; searchParams: Promise<{ focus?: string }> }) {
  const { orgId } = await params;
  const { focus } = await searchParams;
  const t = await getTranslations("drills");
  const lang = ((await getLocale()) as Lang) ?? "de-CH";
  const wanted = (focus ?? "").split(",").filter((f): f is Focus => FOCI.includes(f as Focus));
  const list = wanted.length ? DRILLS.filter((d) => d.focus.some((f) => wanted.includes(f))) : DRILLS;
  return (
    <div className="space-y-6">
      <AreaOrPageHeader title={t("title")} />
      {wanted.length > 0 && <h2 className="text-xl font-bold">{t("suggested")}</h2>}
      <p className="max-w-2xl text-sm text-muted">{t("hint")}</p>
      {/* one scrolling row of underline links (twelve pills filled the first phone screen) */}
      <nav aria-label={t("title")} className="scrollbar-none -mx-1 flex gap-x-4 overflow-x-auto border-b border-foreground/15 px-1 sm:flex-wrap">
        <Link href={`/app/${orgId}/drills`} className={cn("-mb-px min-h-10 shrink-0 whitespace-nowrap border-b-2 pt-2 text-sm font-semibold", !wanted.length ? "border-foreground text-foreground" : "border-transparent text-muted hover:text-foreground")}>
          {t("all")}
        </Link>
        {FOCI.map((f) => (
          <Link
            key={f}
            href={`/app/${orgId}/drills?focus=${f}`}
            aria-current={wanted.length === 1 && wanted[0] === f ? "page" : undefined}
            className={cn("-mb-px min-h-10 shrink-0 whitespace-nowrap border-b-2 pt-2 text-sm font-semibold", wanted.length === 1 && wanted[0] === f ? "border-foreground text-foreground" : "border-transparent text-muted hover:text-foreground")}
          >
            {t(`focus_${f}`)}
          </Link>
        ))}
      </nav>
      <ClubDrills orgId={orgId} focus={wanted} />
      {/* the library: the club's own drills come first, above */}
      <h2 className="text-xl">{t("library")}</h2>
      <ul className="grid border-t-2 border-foreground md:grid-cols-2 md:gap-x-12" data-testid="drills">
        {list.map((d) => (
          <li key={d.id} id={d.id} className="grid scroll-mt-4 grid-cols-[4.5rem_minmax(0,1fr)] gap-x-5 border-b border-foreground/15 py-5 target:bg-surface sm:grid-cols-[6rem_minmax(0,1fr)]">
            <DrillCourt focus={d.focus.find((f) => f !== "finishing") ?? d.focus[0]!} className="w-full" />
            <div className="min-w-0 space-y-2">
              <h2 className="text-lg leading-tight">{d.name[lang] ?? d.name["de-CH"]}</h2>
              <p className="text-[0.9375rem] text-muted">
                {d.focus.map((f) => t(`focus_${f}`)).join(" · ")} · {t("minutes", { minutes: d.minutes })} · {t("players", { players: d.players })} · {t(`level_${d.level}`)}
              </p>
              <p className="text-sm">
                <span className="font-semibold">{t("setup")}: </span>
                {d.setup[lang] ?? d.setup["de-CH"]}
              </p>
              <p className="text-sm">
                <span className="font-semibold">{t("coaching")}: </span>
                {d.coaching[lang] ?? d.coaching["de-CH"]}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

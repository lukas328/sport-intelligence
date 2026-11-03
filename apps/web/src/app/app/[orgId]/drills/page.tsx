import type { Metadata } from "next";
import { DRILLS, type Focus, type Lang } from "@handball/tactics";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { TrainingOrPageHeader } from "@/components/shell/section-nav";
import { cn } from "@/lib/utils";

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
      <TrainingOrPageHeader title={t("title")} />
      {wanted.length > 0 && <h2 className="text-xl font-bold">{t("suggested")}</h2>}
      <p className="max-w-2xl text-sm text-muted">{t("hint")}</p>
      <nav aria-label={t("title")} className="flex flex-wrap gap-1">
        <Link href={`/app/${orgId}/drills`} className={cn("rounded-md px-3.5 py-1.5 text-[0.8125rem] font-medium", !wanted.length ? "bg-foreground text-background" : "bg-raised ring-1 ring-inset ring-border hover:bg-surface")}>
          {t("all")}
        </Link>
        {FOCI.map((f) => (
          <Link
            key={f}
            href={`/app/${orgId}/drills?focus=${f}`}
            aria-current={wanted.length === 1 && wanted[0] === f ? "page" : undefined}
            className={cn("rounded-md px-3.5 py-1.5 text-[0.8125rem] font-medium", wanted.length === 1 && wanted[0] === f ? "bg-foreground text-background" : "bg-raised ring-1 ring-inset ring-border hover:bg-surface")}
          >
            {t(`focus_${f}`)}
          </Link>
        ))}
      </nav>
      <ul className="grid gap-3 md:grid-cols-2" data-testid="drills">
        {list.map((d) => (
          <li key={d.id} id={d.id} className="scroll-mt-4 space-y-2 rounded-lg bg-raised p-5 border border-border target:ring-2 target:ring-accent">
            <h2 className="font-semibold">{d.name[lang] ?? d.name["de-CH"]}</h2>
            <p className="text-xs text-muted">
              {d.focus.map((f) => t(`focus_${f}`)).join(" · ")} · {t("minutes", { minutes: d.minutes })} · {t("players", { players: d.players })} · {t(`level_${d.level}`)}
            </p>
            <p className="text-sm">
              <span className="font-medium">{t("setup")}: </span>
              {d.setup[lang] ?? d.setup["de-CH"]}
            </p>
            <p className="text-sm">
              <span className="font-medium">{t("coaching")}: </span>
              {d.coaching[lang] ?? d.coaching["de-CH"]}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}

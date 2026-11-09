import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Stage, stageButton } from "@/components/domain/stage";
import { IconGoal, IconMatches, IconScenes } from "@/components/shell/icons";

export default async function HomePage() {
  const t = await getTranslations();
  const features = [
    { Icon: IconMatches, title: t("home.f1Title"), body: t("home.f1") },
    { Icon: IconScenes, title: t("home.f2Title"), body: t("home.f2") },
    { Icon: IconGoal, title: t("home.f3Title"), body: t("home.f3") },
  ];
  return (
    <div className="space-y-16 sm:space-y-20">
      <Stage full>
        <h1 className="text-[3rem] leading-[0.92] sm:text-[4.5rem] lg:text-[5.25rem]">{t("app.tagline")}</h1>
        <p className="mt-5 max-w-xl text-lg sm:text-xl">{t("app.description")}</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/register" className={stageButton("solid")}>
            {t("home.cta")}
          </Link>
          <Link href="/login" className={stageButton("outline")}>
            {t("home.login")}
          </Link>
        </div>
        <p className="mt-6 max-w-lg text-[0.9375rem] opacity-90">{t("home.foundation")}</p>
      </Stage>
      <ul className="grid gap-x-12 gap-y-10 sm:grid-cols-3">
        {features.map(({ Icon, title, body }) => (
          <li key={title} className="space-y-2 border-t-2 border-foreground pt-5">
            <Icon className="size-7 text-accent" />
            <h2 className="text-2xl">{title}</h2>
            <p className="text-[0.9375rem] text-muted">{body}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

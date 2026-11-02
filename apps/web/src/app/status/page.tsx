import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { fetchReadiness } from "@/lib/api";
import { formatLatency, toHealthView, type OverallState } from "@/lib/health";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("status");
  return { title: t("title") };
}

const STATE_STYLE: Record<OverallState, string> = {
  ok: "border-ok text-ok",
  degraded: "border-error text-error",
  unreachable: "border-error text-error",
};

export default async function StatusPage() {
  const [t, locale, readiness] = await Promise.all([
    getTranslations("status"),
    getLocale(),
    fetchReadiness(),
  ]);
  const view = toHealthView(readiness);
  const knownNames = new Set(["database", "redis", "storage"]);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-muted">{t("intro")}</p>
      </header>

      <p
        data-testid="overall-status"
        data-state={view.state}
        role="status"
        className={cn("rounded-md border-l-4 bg-surface px-4 py-3 font-medium", STATE_STYLE[view.state])}
      >
        {t(`overall_${view.state}`)}
      </p>

      {view.components.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface text-muted">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium">{t("component")}</th>
                <th scope="col" className="px-4 py-2 font-medium">{t("state")}</th>
                <th scope="col" className="px-4 py-2 text-right font-medium">{t("latency")}</th>
              </tr>
            </thead>
            <tbody>
              {view.components.map((c) => (
                <tr key={c.name} className="border-t border-border" data-testid={`component-${c.name}`}>
                  <td className="px-4 py-2">
                    {knownNames.has(c.name) ? t(`names.${c.name}` as "names.database") : c.name}
                  </td>
                  <td className={cn("px-4 py-2 font-medium", c.status === "ok" ? "text-ok" : "text-error")}>
                    {c.status === "ok" ? t("ok") : `${t("error")} (${c.error ?? "?"})`}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">{formatLatency(c.latency_ms, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {view.version && (
        <p className="text-xs text-muted">{t("version", { version: view.version, env: view.env ?? "" })}</p>
      )}
      <a href="/status" className="text-sm text-accent underline underline-offset-4">
        {t("retry")}
      </a>
    </div>
  );
}

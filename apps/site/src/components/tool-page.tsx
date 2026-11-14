import type { ReactNode } from "react";
import Link from "next/link";
import { Crumbs } from "@/components/crumbs";
import { JsonLd } from "@/components/json-ld";
import { KitScope } from "@/components/kit";
import { PageHead, Updated } from "@/components/wurf-head";
import { messages, type Locale } from "@/lib/i18n";
import { breadcrumbs, graph, webPage } from "@/lib/schema";
import { SITE_UPDATED, pageUrl } from "@/lib/site";

/**
 * Frame of a template or calculator: breadcrumbs (Start / Ratgeber / …), the title, the lead, then
 * the tool, then one link into the guide that explains it. The head is a <header>, so it does not
 * print; only the sheet does.
 */
export function ToolPage({
  locale,
  path,
  title,
  description,
  lead,
  parent,
  more,
  children,
}: {
  locale: Locale;
  path: string;
  title: string;
  description: string;
  lead: string;
  parent?: [string, string];
  more?: [string, string];
  children: ReactNode;
}) {
  const m = messages(locale);
  const trail: [string, string][] = [
    [m.guides.home, `/${locale}/`],
    [m.guides.title, `/${locale}/ratgeber/`],
    ...(parent ? [parent] : []),
  ];
  return (
    <KitScope>
      <JsonLd
        data={graph(
          webPage(locale, path, title, description, SITE_UPDATED),
          breadcrumbs([...trail.map(([n, h]) => [n, pageUrl(locale, h.replace(`/${locale}/`, ""))] as [string, string]), [title, pageUrl(locale, path)]]),
        )}
      />
      <PageHead kick={<Crumbs label={m.nav.crumbs} items={trail} />} title={title} lead={lead}>
        <Updated locale={locale} />
      </PageHead>
      <div className="wrap">
        {children}
        {more && (
          <p className="no-print mt-12 border-t-2 border-ink pt-6">
            <Link href={more[0]} className="link">
              {more[1]}
            </Link>
          </p>
        )}
      </div>
    </KitScope>
  );
}

/** A sheet that prints alone on A4: ink on white, no colour needed. */
export function Sheet({ children }: { children: ReactNode }) {
  return <div className="sheet mt-10 border-2 border-ink bg-paper p-6 md:p-10">{children}</div>;
}

/** A line to write on, with its label underneath. */
export function WriteLine({ label }: { label: string }) {
  return (
    <div className="mt-8">
      <div className="h-8 border-b-2 border-ink" />
      <p className="mt-1 text-base text-ink-2">{label}</p>
    </div>
  );
}

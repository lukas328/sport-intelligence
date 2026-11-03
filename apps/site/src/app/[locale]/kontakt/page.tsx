import type { Metadata } from "next";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";
import { STATUS_URL, SUPPORT_EMAIL } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).contact;
  return pageMeta(locale, "kontakt", t.title, t.lead);
}

export default async function Contact({ params }: Props) {
  const { locale } = await params;
  const t = messages(locale).contact;
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-bold">{t.title}</h1>
      <p className="mt-3 text-lg text-muted">{t.lead}</p>
      <dl className="mt-8 space-y-4">
        <div>
          <dt className="text-sm text-muted">{t.email}</dt>
          <dd className="text-xl font-semibold">
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-accent underline">{SUPPORT_EMAIL}</a>
          </dd>
        </div>
      </dl>
      <p className="mt-6">{t.inApp}</p>
      {STATUS_URL ? (
        <p className="mt-4">
          <a href={STATUS_URL} className="text-accent underline">{t.status}</a>
        </p>
      ) : null}
    </div>
  );
}

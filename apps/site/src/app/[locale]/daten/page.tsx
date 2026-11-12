import type { Metadata } from "next";
import Link from "next/link";
import { KitScope } from "@/components/kit";
import { MailLine } from "@/components/mail-line";
import { PageHead, SectionHead } from "@/components/wurf-head";
import { messages, type Locale } from "@/lib/i18n";
import { pageMeta } from "@/lib/seo";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = messages(locale).data;
  return pageMeta(locale, "daten", t.title, `${t.kick}: ${t.head}`);
}

/** For parents, players and the board: what happens with the video, how consent works. */
export default async function Data({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.data;
  return (
    <KitScope>
      <PageHead kick={t.kick} title={t.head} />
      <div className="wrap">
        <div className="mt-12 grid grid-cols-1 gap-x-16 md:grid-cols-2">
          {t.sections.map((s) => (
            <section key={s.title} className="border-t-2 border-ink py-8" aria-labelledby={`d-${s.title}`}>
              <h2 id={`d-${s.title}`} className="text-[1.75rem] md:text-[2rem]">
                {s.title}
              </h2>
              <p className="measure mt-3">{s.text.includes("{email}") ? <MailLine template={s.text} /> : s.text}</p>
              {"items" in s && s.items && (
                <ul className="measure mt-3">
                  {s.items.map((x) => (
                    <li key={x} className="flex gap-3 border-b border-rule py-3">
                      <i aria-hidden className="mark-band mt-[.5em] h-2 w-3.5 shrink-0" />
                      <span>{x}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
        <section aria-labelledby="board" className="mt-12">
          <SectionHead id="board" title={t.boardTitle} />
          <p className="measure mt-4">{t.board}</p>
          <div className="flex flex-wrap gap-x-8">
            <Link href={`/${locale}/datenschutz/`} className="link">
              {t.privacyLink}
            </Link>
            <Link href={`/${locale}/aufnahme/#notice`} className="link">
              {m.filming.noticeTitle}
            </Link>
          </div>
        </section>
      </div>
    </KitScope>
  );
}

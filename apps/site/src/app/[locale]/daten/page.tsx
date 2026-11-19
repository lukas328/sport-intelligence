import type { Metadata } from "next";
import Link from "next/link";
import { KitScope } from "@/components/kit";
import { MailLine } from "@/components/mail-line";
import { ProductShot } from "@/components/product-shot";
import { appShot, SHOT_SIZES } from "@/lib/product-shots";
import { ConsentArt } from "@/components/head-art";
import { PageHead, SectionHead, Updated } from "@/components/wurf-head";
import { messages, type Locale } from "@/lib/i18n";
import type { Messages } from "@/messages/de";
import { pageMeta } from "@/lib/seo";
import { PAGE_UPDATED } from "@/lib/site";

type Props = { params: Promise<{ locale: Locale }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return pageMeta(locale, "daten", messages(locale).seo.data.title, messages(locale).seo.data.description);
}

/** The four points of the consent, by their names (the part before the colon). */
function consentPoints(t: Messages["data"]): string[] {
  const list = t.sections.find((s) => "items" in s && s.items);
  return list && "items" in list && list.items ? list.items.map((x) => x.split(/\s?:/)[0]!) : [];
}

/** For parents, players and the board: what happens with the video, how consent works. */
export default async function Data({ params }: Props) {
  const { locale } = await params;
  const m = messages(locale);
  const t = m.data;
  return (
    <KitScope>
      <PageHead
        kick={t.kick}
        title={t.head}
        lead={t.lead}
        aside={<ConsentArt title={t.card.title} note={t.card.note} yes={t.card.yes} no={t.card.no} items={consentPoints(t)} />}
      />
      <div className="wrap">
        <div className="mt-12 grid grid-cols-1 gap-x-16 md:grid-cols-2">
          {t.sections.map((s, i) => (
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
              {/* what players and parents get: a link, nothing more (product picture from the app) */}
              {i === 0 && (
                <ProductShot
                  name={appShot("share", locale)}
                  alt={m.home.shareAlt}
                  labels={{}}
                  caption={t.shareCaption}
                  sizes={SHOT_SIZES.half(16)}
                  className="mt-6 max-w-[16rem]"
                />
              )}
            </section>
          ))}
        </div>
        <section aria-labelledby="board" className="mt-12">
          <SectionHead id="board" title={t.boardTitle} />
          <p className="measure mt-4">{t.board}</p>
          <div className="flex flex-wrap gap-x-8">
            <Link href={`/${locale}/datenschutz/`} className="link print-url">
              {t.privacyLink}
            </Link>
            <Link href={`/${locale}/aufnahme/#notice`} className="link print-url">
              {m.filming.noticeTitle}
            </Link>
          </div>
        </section>
        <Updated locale={locale} date={PAGE_UPDATED.daten} />
      </div>
    </KitScope>
  );
}

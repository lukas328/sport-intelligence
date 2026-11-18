import type { ReactNode } from "react";
import type { Messages } from "@/messages/de";

/** a made-up share token: the link looks like a real one, it is not one */
const LINK = "app.handball-intelligence.com/s/q7Lm2xKd";
/** the bubbles: the coach's own in a soft green (the club's), the others white, on a warm cloth */
const OWN = "#d6ebdc";
const CLOTH = "#e9e3d8";

/**
 * Tuesday, before training (BEFUNDE-2 W26, W28, L12): the team chat on a phone, as it really
 * looks when the coach shares a collection. A neutral phone (no maker's mark) and a general
 * messenger (bubbles on a cloth, the own ones green), not any one app's design or name. The link
 * preview is the app's real preview picture of the collection (apps/web lib/share/og-image.tsx,
 * rendered for «Aussen rechts zumachen», 4 scenes) with the real title and description; one earlier
 * message, as sharp as the rest, so the chat looks lived in (U21). Players appear by their shirt
 * numbers only. Everything inside is one picture for screen readers.
 */
export function PhoneChat({ t, locale }: { t: Messages["home"]["chat"]; locale: string }) {
  return (
    <PhoneFrame label={t.label} clock={t.clock}>
      <ChatInside t={t} locale={locale} />
    </PhoneFrame>
  );
}

/** A neutral phone (no maker's mark) with its status bar; everything inside is one picture. */
export function PhoneFrame({ label, clock, children }: { label: string; clock: string; children: ReactNode }) {
  return (
    <div role="img" aria-label={label} className="mx-auto w-[18.5rem] sm:w-[20.5rem]">
      <div aria-hidden className="relative rounded-[3rem] bg-[#121315] p-[0.6rem] shadow-[0_2px_0_1px_#2b2d31_inset,0_30px_60px_-20px_rgb(22_23_26/.55)]">
        {/* the side buttons, quiet */}
        <i className="absolute top-28 -left-[3px] h-10 w-[3px] rounded-l-[2px] bg-[#2b2d31]" />
        <i className="absolute top-40 -left-[3px] h-14 w-[3px] rounded-l-[2px] bg-[#2b2d31]" />
        <i className="absolute top-32 -right-[3px] h-20 w-[3px] rounded-r-[2px] bg-[#2b2d31]" />
        <div className="relative flex aspect-[9/19.5] flex-col overflow-hidden rounded-[2.45rem] bg-[#f7f6f2] text-[#16171a]">
          {/* status bar with a neutral camera notch */}
          <div className="relative flex h-10 shrink-0 items-center justify-between px-7 pt-1 text-[0.8125rem] font-semibold">
            <span>{clock}</span>
            <i className="absolute top-2.5 left-1/2 h-[1.4rem] w-[5.5rem] -translate-x-1/2 rounded-[999px] bg-[#0b0c0d]" />
            <span className="flex items-center gap-1.5">
              <svg viewBox="0 0 18 12" className="h-2.5 w-4">
                <rect x="0" y="8" width="3" height="4" rx="0.8" fill="currentColor" />
                <rect x="5" y="5.5" width="3" height="6.5" rx="0.8" fill="currentColor" />
                <rect x="10" y="3" width="3" height="9" rx="0.8" fill="currentColor" />
                <rect x="15" y="0" width="3" height="12" rx="0.8" fill="currentColor" />
              </svg>
              <svg viewBox="0 0 26 12" className="h-3 w-6">
                <rect x="0.75" y="0.75" width="21.5" height="10.5" rx="3" fill="none" stroke="currentColor" strokeOpacity={0.45} strokeWidth={1.5} />
                <rect x="2.5" y="2.5" width="15" height="7" rx="1.6" fill="currentColor" />
                <rect x="23.5" y="4" width="2" height="4" rx="1" fill="currentColor" fillOpacity={0.45} />
              </svg>
            </span>
          </div>
          {children}
          <i className="absolute bottom-1.5 left-1/2 h-1 w-28 -translate-x-1/2 rounded-[999px] bg-black/80" />
        </div>
      </div>
    </div>
  );
}

function ChatInside({ t, locale }: { t: Messages["home"]["chat"]; locale: string }) {
  return (
    <>
          {/* the group */}
          <div className="flex shrink-0 items-center gap-2.5 border-b border-black/10 px-3 pb-2.5">
            <svg viewBox="0 0 12 20" className="h-4 w-2.5 text-[#10684a]">
              <path d="M10 2 2 10l8 8" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="grid size-9 shrink-0 place-items-center rounded-[999px] bg-[#10684a] font-slant text-[0.9375rem] text-white">H1</span>
            <span className="min-w-0 leading-tight">
              <b className="block truncate text-[0.9375rem]">{t.group}</b>
              <span className="block text-[0.75rem] text-ink-2">{t.members}</span>
            </span>
          </div>

          {/* the conversation */}
          <div
            className="flex flex-1 flex-col justify-end gap-1.5 overflow-hidden px-2.5 pt-2 pb-2.5"
            style={{
              backgroundColor: CLOTH,
              backgroundImage: "radial-gradient(rgb(22 23 26 / .06) 1px, transparent 1.3px)",
              backgroundSize: "14px 14px",
            }}
          >
            {/* one earlier message, sharp like the rest (U21): the chat is lived in, nothing looks broken */}
            <div className="max-w-[78%] rounded-[0.9rem] rounded-tl-[0.3rem] bg-white px-2.5 py-1.5 shadow-[0_1px_0_rgb(0_0_0/.08)]">
              <b className="block text-[0.75rem] text-[#9a4b1d]">{t.earlier.from}</b>
              <span className="block text-[0.8125rem] leading-snug">{t.earlier.text}</span>
              <span className="block text-right text-[0.6875rem] text-ink-2">{t.earlier.time}</span>
            </div>
            <span className="mx-auto my-1 rounded-[999px] bg-white/85 px-3 py-0.5 text-[0.75rem] font-semibold text-ink-2 shadow-[0_1px_0_rgb(0_0_0/.06)]">{t.day}</span>

            {/* the coach's message with the preview of the link */}
            <div className="ml-auto w-[88%] rounded-[0.9rem] rounded-tr-[0.3rem] p-1 shadow-[0_1px_0_rgb(0_0_0/.08)]" style={{ backgroundColor: OWN }}>
              <div className="overflow-hidden rounded-[0.65rem] bg-black/[.05]">
                <img src={`/media/teilen-vorschau-${locale}.webp`} alt="" width={640} height={336} loading="lazy" decoding="async" className="block aspect-[1200/630] w-full object-cover" />
                <div className="px-2.5 pt-1.5 pb-2 leading-snug">
                  <b className="block text-[0.8125rem]">{t.previewTitle}</b>
                  <span className="block text-[0.75rem] text-ink-2">{t.previewText}</span>
                  <span className="block text-[0.6875rem] text-ink-2">app.handball-intelligence.com</span>
                </div>
              </div>
              <p className="px-1.5 pt-1.5 text-[0.875rem] leading-snug">
                {t.message} <span className="break-all text-[#0e6a8a] underline">{LINK}</span>
              </p>
              <p className="px-1.5 text-right text-[0.6875rem] text-ink-2">{t.time}</p>
            </div>

            {/* a player who saw it himself */}
            <div className="max-w-[80%] rounded-[0.9rem] rounded-tl-[0.3rem] bg-white px-2.5 py-1.5 shadow-[0_1px_0_rgb(0_0_0/.08)]">
              <b className="block text-[0.75rem] text-[#9a4b1d]">{t.replyFrom}</b>
              <span className="block text-[0.875rem] leading-snug">{t.reply}</span>
              <span className="block text-right text-[0.6875rem] text-ink-2">{t.replyTime}</span>
            </div>
          </div>

          {/* the field to write in */}
          <div className="flex shrink-0 items-center gap-2 bg-[#f7f6f2] px-2.5 pt-2 pb-5">
            <span className="flex-1 rounded-[999px] border border-black/10 bg-white px-3.5 py-1.5 text-[0.8125rem] text-[#6b6e73]">{t.input}</span>
            <span className="grid size-8 shrink-0 place-items-center rounded-[999px] bg-[#10684a] text-white">
              <svg viewBox="0 0 16 16" className="size-3.5">
                <path d="M2 8h11M9 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          </div>
    </>
  );
}

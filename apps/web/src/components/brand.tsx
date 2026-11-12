import { cn } from "@/lib/utils";

/*
 * The logo «Taktik» (docs/design/brand2/taktik/README.md). Inside the app only ink: the colours
 * belong to the teams there. Outside the app (sign-in, onboarding, public pages) the two-coloured
 * word mark. The files come unchanged from docs/design/brand2/taktik/final/.
 */

/** The mark in ink, in front of the club crest in the app. 32-px drawing below 48 px. */
export function AppMark({ className, size = 24 }: { className?: string; size?: number }) {
  return <img src={size < 48 ? "/brand/favicon-32-tinte.svg" : "/brand/zeichen-tinte.svg"} alt="" width={size} height={size} className={cn("shrink-0", className)} />;
}

/** The two-coloured word mark «Handball Intelligence», outside the app; at least 220 px wide. */
export function BrandWordmark({ name, className }: { name: string; className?: string }) {
  return <img src="/brand/wortmarke-quer.svg" alt={name} width={231} height={55} className={cn("h-[55px] w-auto", className)} />;
}

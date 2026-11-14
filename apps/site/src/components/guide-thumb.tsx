/**
 * The small picture of each guide in the list: a miniature of its own drawing, or the one number the
 * guide is about. Decoration next to a link that names the guide, so hidden from screen readers.
 */
import { CourtLines, HalfCourtLines } from "@/components/anlauf/court";

const NUMBER: Record<string, string> = {
  "videoanalyse-amateurteam": "3",
  "spiel-auswerten-20-minuten": "20′",
  "wurfquote-torhueterquote": "%",
  "szenen-im-training-zeigen": "10′",
  "video-im-verein-einwilligung": "16",
  "handball-begriffe": "5:1",
  "wege-zur-videoanalyse": "4",
};

export function GuideThumb({ slug }: { slug: string }) {
  const box = "flex size-20 shrink-0 items-center justify-center border-2 border-ink bg-paper";
  if (slug === "handballspiel-filmen" || slug === "aufnahme") {
    return (
      <span aria-hidden className={box}>
        <svg viewBox="-4 -4 48 40" className="w-[4.25rem]">
          <path d="M20 31 L-4 17 L-4 -4 L44 -4 L44 17 Z" fill="var(--club)" fillOpacity={0.18} />
          <CourtLines line="var(--ink)" width={1.4} />
          <rect x={17.5} y={30} width={5} height={3} fill="var(--ink)" />
        </svg>
      </span>
    );
  }
  if (slug === "gegentore-nach-position") {
    return (
      <span aria-hidden className={box}>
        <svg viewBox="-0.6 -1.2 21.2 17.2" className="w-[4.25rem]">
          <HalfCourtLines opacity={0.7} />
          {[
            [4.6, 10.2, 1.1],
            [10, 11.6, 1.5],
            [15.4, 10.2, 2.4],
          ].map(([x, y, r]) => (
            <circle key={x} cx={x} cy={y} r={r} fill="var(--club)" fillOpacity={0.25} stroke="var(--club-line)" strokeWidth={0.3} />
          ))}
        </svg>
      </span>
    );
  }
  if (slug === "gegenstoss-und-ballverluste") {
    return (
      <span aria-hidden className={box}>
        <svg viewBox="0 0 60 30" className="w-[4.25rem]">
          <path d="M2 15H58" stroke="var(--ink)" strokeWidth={1} />
          {[8, 20, 34, 37, 40, 52].map((x) => (
            <rect key={x} x={x - 1.2} y={6} width={2.4} height={9} fill="var(--club)" />
          ))}
          {[36, 41].map((x) => (
            <rect key={x} x={x - 1.2} y={15} width={2.4} height={8} fill="var(--ink)" />
          ))}
        </svg>
      </span>
    );
  }
  return (
    <span aria-hidden className={box}>
      <span className="font-num text-[1.875rem] leading-none text-club-text">{NUMBER[slug] ?? "?"}</span>
    </span>
  );
}

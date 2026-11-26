"use client";

import { Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/card";
import { FramesProvider, InlinePersonPlayer, PersonStill } from "@/components/video/person-still";
import { REFEREE_PICK, kitWarnings, type KitKey, type Kits, type TeamKitKey } from "@/lib/kit";
import { cn } from "@/lib/utils";
import { peopleOf, useKitPictures, type KitPictures } from "./kit-people";

const TEAM_KITS = [
  ["own", "matches.kitOwn"],
  ["own_gk", "matches.kitOwnGk"],
  ["opponent", "matches.kitOpp"],
  ["opponent_gk", "matches.kitOppGk"],
] as const satisfies readonly (readonly [TeamKitKey, string])[];

const SWATCH =
  "relative grid size-9 shrink-0 place-items-center has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent";

/** A shirt in the kit's colour: the swatch looks like what it stands for. */
function Shirt({ colour, empty = false }: { colour?: string; empty?: boolean }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-9">
      <path
        d="M8 3 4.2 4.8 2 9l3.2 1.6L6.4 9v12h11.2V9l1.2 1.6L22 9l-2.2-4.2L16 3c-.9 1.4-2.3 2.2-4 2.2S8.9 4.4 8 3Z"
        fill={empty ? "none" : colour}
        stroke="currentColor"
        strokeOpacity={empty ? 0.6 : 0.35}
        strokeWidth="1"
        strokeDasharray={empty ? "2 1.5" : undefined}
        strokeLinejoin="round"
      />
    </svg>
  );
}
const PICKER = "absolute inset-0 size-full cursor-pointer opacity-0";

/** The kit colours of a match as colour swatches: four team kits and the optional referee kit,
 * with the warning when two of them are hard to tell apart. Used by the new and the edit form and
 * at the upload (K2). `presets`: the club's home and away shirt as one tap for our shirt; `only`:
 * just these swatches (the upload asks for our kits only). `pictures`: the video of the match;
 * once its analysis is ready each colour shows the people the analysis put in it, and a tap plays
 * one right here (Lukas: sort with the video in the step). */
export function KitFields({
  kits,
  onChange,
  unknown = [],
  presets,
  only,
  names,
  pictures,
}: {
  kits: Kits;
  /** an observed match: both teams by name, nothing is «Eigene» (BUG-05) */
  names?: { own: string; opp: string } | null;
  onChange: (kits: Kits) => void;
  unknown?: readonly TeamKitKey[];
  presets?: { home: string; away: string | null } | null;
  only?: readonly TeamKitKey[];
  pictures?: { orgId: string; videoId: string } | null;
}) {
  const t = useTranslations();
  const pics = useKitPictures(pictures);
  const [playing, setPlaying] = useState<KitPictures["tracks"][number] | null>(null);
  const who = (n: number, number: number | null) =>
    number != null ? `#${number}` : t("matches.kitPerson", { n });
  // the people of one colour under its swatch: a few stills, a tap plays one above the colours
  const people = (k: KitKey): ReactNode => {
    if (!pics) return null;
    const list = peopleOf(pics.tracks, k);
    if (!list.length)
      return (
        <p className="m-0 text-xs text-muted" data-testid={`kit-nobody-${k}`}>
          {t("matches.kitNobody")}
        </p>
      );
    return (
      <span className="flex gap-1.5" data-testid={`kit-people-${k}`}>
        {list.map((tr) => (
          <button
            key={tr.track_no}
            type="button"
            className="min-h-11 cursor-pointer border-0 bg-transparent p-0"
            aria-pressed={playing?.track_no === tr.track_no}
            aria-label={t("matches.kitPlay", { who: who(tr.track_no, tr.number) })}
            onClick={() => setPlaying(tr)}
          >
            <PersonStill
              geometry={pics.geometry}
              tracksUrl={`${pics.video}/tracks`}
              chunkMs={pics.chunkMs}
              track={tr.track_no}
              at={tr.first_ms + Math.min(2000, (tr.last_ms - tr.first_ms) / 2)}
              label={who(tr.track_no, tr.number)}
              className={cn(
                "h-12 w-9",
                playing?.track_no === tr.track_no && "outline-2 outline-offset-1 outline-ink",
              )}
            />
          </button>
        ))}
      </span>
    );
  };
  const hintId = useId();
  const shown = only ? TEAM_KITS.filter(([k]) => only.includes(k)) : TEAM_KITS;
  const same = (a: string | null | undefined, b: string | null | undefined) =>
    Boolean(a && b && a.toLowerCase() === b.toLowerCase());
  // a kit nobody chose stays empty and is not compared (third real-video test G7: the form
  // filled the opponent in red and warned of «Ähnliche Farben» for a red club)
  const isOpen = (k: TeamKitKey) => unknown.includes(k);
  // the hint on similar colours only after a choice here (finding A11): before, it stood under
  // the defaults and read like an error
  const [touched, setTouched] = useState(false);
  const similar = touched
    ? kitWarnings({ ...kits, ...Object.fromEntries(unknown.map((k) => [k, null])) })
    : [];
  const pick = (next: Kits) => {
    setTouched(true);
    onChange(next);
  };
  const referee = `${t("matches.kitReferee")} (${t("common.optional")})`;
  const labelOf = (k: TeamKitKey, key: string) =>
    names
      ? t(k.endsWith("_gk") ? "matches.kitKeeperOf" : "matches.kitFieldOf", {
          team: k.startsWith("own") ? names.own : names.opp,
        })
      : t(key as "matches.kitOwn");
  const body = (
    <>
      {presets && (
        <div
          className="mb-3 flex flex-wrap items-center gap-2"
          role="group"
          aria-label={t("matches.kitPresets")}
          data-testid="kit-presets"
        >
          {(
            [
              ["home", presets.home],
              ["away", presets.away],
            ] as const
          ).map(([which, colour]) =>
            colour ? (
              <button
                key={which}
                type="button"
                aria-pressed={same(kits.own, colour)}
                onClick={() => pick({ ...kits, own: colour })}
                className={cn(
                  "inline-flex min-h-11 cursor-pointer items-center gap-2 border-2 px-3 text-[15px] font-bold",
                  same(kits.own, colour)
                    ? "border-ink bg-ink text-ground"
                    : "border-ink bg-transparent text-ink",
                )}
                data-testid={`kit-preset-${which}`}
              >
                <i
                  aria-hidden
                  className="block size-5 shadow-[0_0_0_1.5px_currentColor]"
                  style={{ background: colour }}
                />
                {t(which === "home" ? "matches.kitHome" : "matches.kitAway")}
              </button>
            ) : null,
          )}
        </div>
      )}
      {pics && playing && (
        <InlinePersonPlayer
          className="mb-3"
          video={pics.video}
          track={playing}
          geometry={pics.geometry}
          chunkMs={pics.chunkMs}
          title={t("matches.kitPlaying", { who: who(playing.track_no, playing.number) })}
          closeLabel={t("matches.kitClosePlayer")}
          onClose={() => setPlaying(null)}
          testId="kit-player"
        />
      )}
      <div className="flex flex-wrap gap-x-5 gap-y-3">
        {shown.map(([k, label]) => (
          <div key={k} className="flex flex-col gap-1.5">
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <span
                className={cn(SWATCH, isOpen(k) && "text-muted")}
                data-testid={`kit-${k}`}
                data-open={isOpen(k) || undefined}
              >
                <Shirt colour={isOpen(k) ? undefined : kits[k]} empty={isOpen(k)} />
                {isOpen(k) && <Plus aria-hidden className="absolute size-3.5" />}
                <input
                  aria-label={labelOf(k, label)}
                  name={`kit_${k}`}
                  type="color"
                  value={kits[k]}
                  onChange={(e) => pick({ ...kits, [k]: e.target.value })}
                  className={PICKER}
                />
              </span>
              {labelOf(k, label)}
            </label>
            {people(k)}
          </div>
        ))}
        {!only && (
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <span
                  className={cn(SWATCH, !kits.referee && "text-muted")}
                  data-testid="kit-referee"
                >
                  <Shirt colour={kits.referee ?? undefined} empty={!kits.referee} />
                  {!kits.referee && <Plus aria-hidden className="absolute size-3.5" />}
                  <input
                    aria-label={referee}
                    aria-describedby={hintId}
                    name="kit_referee"
                    type="color"
                    value={kits.referee ?? REFEREE_PICK}
                    onChange={(e) => pick({ ...kits, referee: e.target.value })}
                    className={PICKER}
                  />
                </span>
                {referee}
              </label>
              {kits.referee && (
                <Button
                  type="button"
                  variant="quiet"
                  size="icon-sm"
                  className="-my-1"
                  aria-label={t("matches.kitRefereeClear")}
                  title={t("matches.kitRefereeClear")}
                  onClick={() => onChange({ ...kits, referee: null })}
                >
                  <X aria-hidden />
                </Button>
              )}
            </div>
            {people("referee")}
          </div>
        )}
      </div>
      <p className="mt-2 text-xs text-muted">{t("matches.kitsHint")}</p>
      {pics && <p className="mt-1 text-xs text-muted">{t("matches.kitPeopleHint")}</p>}
      {!only && (
        <p id={hintId} className="mt-1 text-xs text-muted">
          {t("matches.kitRefereeHint")}
        </p>
      )}
      {similar.length > 0 && (
        <Alert kind="info" className="mt-3">
          <span data-testid="kit-warning">
            {t("matchForm.kitWarning", {
              pairs: similar
                .map(([a, b]) => `${t(`matchForm.kit_${a}`)} / ${t(`matchForm.kit_${b}`)}`)
                .join(", "),
            })}
          </span>
        </Alert>
      )}
    </>
  );
  // one hidden video for all stills of the colours
  return pics ? (
    <FramesProvider src={`${pics.video}/media/hls/master.m3u8`}>{body}</FramesProvider>
  ) : (
    body
  );
}

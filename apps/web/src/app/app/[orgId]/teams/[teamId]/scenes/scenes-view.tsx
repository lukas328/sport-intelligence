"use client";

import type { Schemas } from "@handball/api-client";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useFormatter, useTranslations } from "next-intl";
import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { linkClass, SectionHead } from "@/components/anlauf/blocks";
import { Bundle, EmptyField } from "@/components/anlauf/bundle";
import { clockOf } from "@/components/anlauf/three-things-view";
import { useShell } from "@/components/shell/context";
import { buttonClass } from "@/components/ui/button";
import { api } from "@/lib/client";
import { chipsFromText } from "@/lib/scene-words";
import { matchStyle } from "@/lib/color";
import { goalRuns, useMatchGraphics } from "@/lib/graphics";
import { threeThings } from "@/lib/three-things";

type Match = Schemas["MatchSummary"];
type Hit = Schemas["SearchHit"];
type Filter = Schemas["SearchFilter"];

/** The chips of the search (SPEC 7.6): the existing filters, each a word the coach would say. */
type ChipGroup = "event" | "position" | "range";
interface Chip {
  key: string;
  group: ChipGroup;
  filter: (ctx: { lastMatch: string | null; last3: string[] }) => Partial<Filter>;
}

const CHIPS: Chip[] = [
  { key: "conceded", group: "event", filter: () => ({ types: ["shot"], outcomes: ["goal"], sides: ["opponent"] }) },
  { key: "scored", group: "event", filter: () => ({ types: ["shot"], outcomes: ["goal"], sides: ["own"] }) },
  { key: "saves", group: "event", filter: () => ({ types: ["shot"], outcomes: ["save"], sides: ["opponent"] }) },
  { key: "turnovers", group: "event", filter: () => ({ types: ["turnover"], sides: ["own"] }) },
  { key: "wing_right", group: "position", filter: () => ({ shot_zones: ["wing_right"] }) },
  { key: "wing_left", group: "position", filter: () => ({ shot_zones: ["wing_left"] }) },
  { key: "back_left", group: "position", filter: () => ({ shot_zones: ["back_left", "half_left"] }) },
  { key: "back_centre", group: "position", filter: () => ({ shot_zones: ["back_centre", "half_centre"] }) },
  { key: "back_right", group: "position", filter: () => ({ shot_zones: ["back_right", "half_right"] }) },
  { key: "circle", group: "position", filter: () => ({ shot_zones: ["circle_left", "circle_centre", "circle_right"] }) },
  { key: "last_match", group: "range", filter: ({ lastMatch }) => (lastMatch ? { match_ids: [lastMatch] } : {}) },
  { key: "last_3", group: "range", filter: ({ last3 }) => (last3.length ? { match_ids: last3 } : {}) },
];

const TILES = 8;

/** zones of the graphics as position chips */
const ZONE_CHIP: Record<string, string> = { ra: "wing_right", la: "wing_left", rl: "back_left", rm: "back_centre", rr: "back_right", kr: "circle" };

function combine(chips: Chip[], ctx: { lastMatch: string | null; last3: string[] }): Filter {
  const f: Record<string, unknown> = {};
  for (const c of chips) for (const [k, v] of Object.entries(c.filter(ctx))) f[k] = v;
  return f as Filter;
}

/**
 * Szenen (SPEC 7.6): the search field with the active filters as chips, the answer as a large
 * figure with its base, the actions, the scenes as tiles. A scene is a stretch with a video
 * time: events without one are figures, not scenes, and are neither shown nor counted.
 */
export function ScenesView({ orgId, teamId, matches, side }: { orgId: string; teamId: string; matches: Match[]; side: React.ReactNode }) {
  const t = useTranslations("scenesPage");
  const router = useRouter();
  // ?chips=conceded,wing_right opens a search from elsewhere (the season, a thing)
  const params = useSearchParams();
  const asked = params.get("chips");
  // ?q=a sentence (from «Suchen» or the palette): its words become chips, the rest stays text
  const sentence = params.get("q");
  const withVideo = useMemo(() => matches.filter((m) => m.has_video).sort((a, b) => b.kickoff_at.localeCompare(a.kickoff_at)), [matches]);
  const ctx = { lastMatch: withVideo[0]?.id ?? null, last3: withVideo.slice(0, 3).map((m) => m.id) };
  // the page opens on the first thing of the last match (as the start says it), over the last
  // three matches: an answer, not a list
  const lastGraphics = useMatchGraphics(orgId, ctx.lastMatch ?? "");
  const firstThing = lastGraphics.data ? threeThings(goalRuns(lastGraphics.data))[0] : undefined;
  const [picked, setActive] = useState<string[] | null>(() => {
    const keys = asked?.split(",").filter((k) => CHIPS.some((c) => c.key === k)) ?? [];
    if (keys.length) return keys;
    if (sentence) return chipsFromText(sentence);
    return null;
  });
  const start = firstThing
    ? [firstThing.team === "opp" ? "conceded" : "scored", ...(ZONE_CHIP[firstThing.zone ?? ""] ? [ZONE_CHIP[firstThing.zone ?? ""]!] : []), "last_3"]
    : [];
  const active = picked ?? start;
  // «Suchen» (?focus=1) and a sentence (?q=) put the cursor in the field, also when the page is open
  const field = useRef<HTMLInputElement>(null);
  const wantsFocus = params.get("focus") === "1" || sentence != null;
  useEffect(() => {
    if (wantsFocus) field.current?.focus();
  }, [wantsFocus, params]);
  const [text, setText] = useState(() => (sentence && chipsFromText(sentence).length === 0 ? sentence : ""));
  const [shown, setShown] = useState(TILES);
  const chips = CHIPS.filter((c) => active.includes(c.key));
  // without a filter: the newest scenes of the last match, never a raw list
  const scope = chips.length ? chips : CHIPS.filter((c) => c.key === "last_match");
  const filter = combine(scope, ctx);
  // the base of the answer: the same search without the position
  const baseChips = scope.filter((c) => c.group !== "position");
  const hasBase = baseChips.length !== scope.length;
  const path = { org_id: orgId, team_id: teamId };
  const result = useQuery({
    queryKey: ["scenes", teamId, filter],
    queryFn: async () => (await api.POST("/v1/orgs/{org_id}/teams/{team_id}/search", { params: { path }, body: { ...filter, limit: 500 } })).data ?? null,
  });
  const base = useQuery({
    queryKey: ["scenes", teamId, combine(baseChips, ctx)],
    enabled: hasBase,
    queryFn: async () => (await api.POST("/v1/orgs/{org_id}/teams/{team_id}/search", { params: { path }, body: { ...combine(baseChips, ctx), limit: 500 } })).data ?? null,
  });
  const scenes = (result.data?.hits ?? []).filter((h) => h.video_id && h.t_ms != null).sort((a, b) => b.kickoff_at.localeCompare(a.kickoff_at) || (b.t_ms ?? 0) - (a.t_ms ?? 0));
  const baseCount = (base.data?.hits ?? []).filter((h) => h.video_id && h.t_ms != null).length;
  const label = (c: Chip) => t(`chip.${c.key}` as "chip.conceded");
  // the same answer in the last match, as the base for a comparison
  const inLast = (hits: Hit[]) => hits.filter((h) => h.match_id === ctx.lastMatch && h.video_id && h.t_ms != null).length;
  const lastCount = inLast(result.data?.hits ?? []);
  const lastBase = inLast(base.data?.hits ?? []);
  const lastName = withVideo[0]?.opponent_name.split(/[\s-]/).find((w) => w.length > 3) ?? null;
  const suggestions = CHIPS.filter((c) => !active.includes(c.key) && (!text || label(c).toLowerCase().includes(text.toLowerCase())));
  const toggle = (k: string) => {
    const chip = CHIPS.find((c) => c.key === k)!;
    // one chip per group: a new event or position replaces the old one
    setActive(active.includes(k) ? active.filter((x) => x !== k) : [...active.filter((x) => CHIPS.find((c) => c.key === x)?.group !== chip.group), k]);
    setShown(TILES);
    setText("");
  };
  const event = chips.find((c) => c.group === "event");
  const position = chips.find((c) => c.group === "position");

  const collect = useMutation({
    mutationFn: async () => {
      const r = await api.POST("/v1/orgs/{org_id}/teams/{team_id}/collections", {
        params: { path },
        body: {
          title: [event, position].filter(Boolean).map((c) => label(c!)).join(", ") || t("defaultTitle"),
          items: scenes.slice(0, 40).map((h) => ({ kind: "scene" as const, match_id: h.match_id, event_id: h.kind === "event" ? h.id : null, start_ms: h.start_ms, end_ms: h.end_ms, title: h.title })),
        },
      });
      if (r.error || !r.data) throw r.error;
      return r.data;
    },
    onSuccess: (c) => router.push(`/app/${orgId}/collections/${c.id}`),
  });

  return (
    <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0">
        <label className="flex min-h-16 items-center gap-3 border-2 border-ink bg-paper px-[18px] text-xl font-semibold">
          <Search aria-hidden className="size-[22px] shrink-0" strokeWidth={2.2} />
          <span className="sr-only">{t("searchLabel")}</span>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key !== "Enter") return;
              // a sentence: its words become the chips; otherwise the first matching chip
              const words = chipsFromText(text);
              if (words.length) {
                setActive(words);
                setText("");
                setShown(TILES);
              } else if (suggestions[0]) toggle(suggestions[0].key);
            }}
            ref={field}
            placeholder={chips.length ? chips.map(label).join(", ") : t("placeholder")}
            className="min-w-0 flex-1 bg-transparent font-semibold outline-none placeholder:text-ink"
            data-testid="scene-search"
          />
        </label>
        <div className="mt-3 flex flex-wrap gap-2" aria-label={t("filters")}>
          {chips.map((c) => (
            <button key={c.key} type="button" aria-pressed onClick={() => toggle(c.key)} className="inline-flex min-h-11 cursor-pointer items-center border-[1.5px] border-ink bg-ink px-3.5 text-[15px] font-semibold text-ground">
              {label(c)}
            </button>
          ))}
          {suggestions.slice(0, chips.length ? 5 : 8).map((c) => (
            <button key={c.key} type="button" aria-pressed={false} onClick={() => toggle(c.key)} className="inline-flex min-h-11 cursor-pointer items-center border-[1.5px] border-dashed border-ink bg-transparent px-3.5 text-[15px] font-semibold text-ink-2">
              {label(c)}
            </button>
          ))}
        </div>

        {result.data && (
          <div className="mt-7 flex flex-wrap items-baseline gap-4" data-testid="scene-answer">
            <b className="font-num text-[64px] leading-[.8] md:text-[96px]">{scenes.length}</b>
            <p className="m-0 max-w-[40ch] text-xl font-bold">
              {hasBase
                ? t("answerOf", { base: baseCount, what: event ? t(`plural.${event.key}` as "plural.conceded") : t("scenesWord"), where: position ? t(`where.${position.key}` as "where.wing_right") : "" })
                : chips.length
                  ? t("answerScenes", { what: chips.map(label).join(", ") })
                  : t("answerLast")}
              {hasBase && baseCount > 0 && (
                <span className="mt-1 block text-[17px] font-normal text-ink-2">
                  {t("sharePct", { pct: Math.round((scenes.length / baseCount) * 100) })}
                  {lastName && lastBase > 0 && ` ${t("inLast", { opponent: lastName, n: lastCount, base: lastBase })}`}
                </span>
              )}
            </p>
          </div>
        )}
        <div className="mt-5 flex flex-wrap items-center gap-3">
          {scenes[0] && (
            <Link href={`/app/${orgId}/matches/${scenes[0].match_id}?tab=video&t=${scenes[0].start_ms ?? scenes[0].t_ms ?? 0}`} className={buttonClass("primary")}>
              {t("playAll", { n: scenes.length })}
            </Link>
          )}
          {scenes.length > 0 && (
            <button type="button" className={buttonClass("secondary")} onClick={() => collect.mutate()} disabled={collect.isPending}>
              {t("toCollection")}
            </button>
          )}
          <Link href={`/app/${orgId}/teams/${teamId}/matrix`} className={linkClass}>
            {t("asTable")}
          </Link>
        </div>

        <section className="mt-10" aria-labelledby="scene-tiles">
          <SectionHead title={<span id="scene-tiles">{t("count", { n: scenes.length })}</span>} note={t("newestFirst")} />
          {scenes.length === 0 && result.data ? (
            <p className="text-[17px] text-ink-2">{t("none")}</p>
          ) : (
            <ul className="m-0 grid list-none grid-cols-2 gap-x-3.5 gap-y-[18px] p-0 md:grid-cols-4 md:gap-x-5 md:gap-y-6" data-testid="scene-tiles">
              {scenes.slice(0, shown).map((h) => (
                <li key={h.id}>
                  <SceneTile orgId={orgId} hit={h} match={matches.find((m) => m.id === h.match_id)} />
                </li>
              ))}
            </ul>
          )}
          {scenes.length > shown && (
            <button type="button" onClick={() => setShown((s) => s + TILES * 2)} className="mt-5 min-h-11 cursor-pointer font-bold underline decoration-[1.5px] underline-offset-4">
              {t("more", { n: scenes.length - shown })}
            </button>
          )}
        </section>
      </div>
      <aside className="flex min-w-0 flex-col gap-8">{side}</aside>
    </div>
  );
}

const ms = (v: number) => `${Math.floor(v / 60000)}:${String(Math.round((v % 60000) / 1000)).padStart(2, "0")}`;

/** One scene: the Minifeld with its run (goals) or empty, time, match, one line, length. */
function SceneTile({ orgId, hit, match }: { orgId: string; hit: Hit; match: Match | undefined }) {
  const t = useTranslations("scenesPage");
  const format = useFormatter();
  const { org } = useShell();
  const g = useMatchGraphics(orgId, hit.match_id);
  const goal = g.data && hit.kind === "event" ? goalRuns(g.data).find((x) => x.eventId === hit.id) : undefined;
  const opp = (match?.opponent_name ?? hit.match_label).split(/[\s-]/).find((w) => w.length > 3) ?? hit.match_label;
  const kind = hit.type === "shot" ? (hit.outcome === "goal" ? t("goal") : hit.outcome === "save" ? t("save") : t("shot")) : hit.type === "turnover" ? t("turnover") : (hit.title ?? hit.type);
  const what = `${kind}${hit.number != null ? `, ${t("numberRead", { n: hit.number })}` : ""}${goal && !goal.confirmed ? `, ${t("spotEstimated")}` : ""}`;
  return (
    <Link
      href={`/app/${orgId}/matches/${hit.match_id}?tab=video&t=${hit.start_ms ?? hit.t_ms ?? 0}`}
      className="flex flex-col gap-1.5 text-ink no-underline"
      style={matchStyle([org.primary_color, org.secondary_color ?? null], match?.opponent_color ? [match.opponent_color] : null) as CSSProperties}
    >
      {goal ? <Bundle goals={[goal]} width={200} label={what ?? ""} /> : <EmptyField />}
      {/* the match clock where the analysis knows it; otherwise the place in the video */}
      {goal?.minute != null ? <b className="font-num text-[17px] md:text-xl">{clockOf(goal.minute)}</b> : <b className="text-[15px] font-bold">{t("videoAt", { time: ms(hit.t_ms ?? hit.start_ms ?? 0) })}</b>}
      <span className="text-[13px] leading-snug text-ink-2 md:text-[15px]">
        {format.dateTime(new Date(hit.kickoff_at), { day: "numeric", month: "numeric" })} {opp} · {what}
      </span>
      <span className="font-mono text-[13px] font-semibold text-ink-2">{ms(Math.max(0, (hit.end_ms ?? 0) - (hit.start_ms ?? 0)))}</span>
    </Link>
  );
}

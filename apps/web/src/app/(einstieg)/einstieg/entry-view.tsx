"use client";

import type { Schemas } from "@handball/api-client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { type CSSProperties, type FormEvent, useEffect, useState } from "react";
import { SectionHead } from "@/components/anlauf/blocks";
import { Bundle } from "@/components/anlauf/bundle";
import { WurfHead } from "@/components/anlauf/heads";
import { useThingText } from "@/components/anlauf/three-things-view";
import { buttonClass } from "@/components/ui/button";
import { api } from "@/lib/client";
import { clubStyle, SHIRTS } from "@/lib/color";
import { goalRuns, type MatchGraphics } from "@/lib/graphics";
import { threeThings } from "@/lib/three-things";
import { cn } from "@/lib/utils";

type Hit = Schemas["PublicTeamHit"];
type Preview = Schemas["PublicTeamPreview"];

/** The website's colour words (?farbe=) and the eight shirts of the app. */
export const FARBE: Record<string, string> = {
  blau: SHIRTS[0][1],
  rot: SHIRTS[1][1],
  gelb: SHIRTS[2][1],
  schwarz: SHIRTS[3][1],
  weiss: SHIRTS[4][1],
  gruen: SHIRTS[5][1],
  orange: SHIRTS[6][1],
  violett: SHIRTS[7][1],
};
const WORD_OF = Object.fromEntries(Object.entries(FARBE).map(([w, hex]) => [hex, w]));
const SECOND = (hex: string) => (hex === SHIRTS[4][1] || hex === SHIRTS[2][1] ? SHIRTS[3][1] : SHIRTS[4][1]);

/**
 * The public entry (UX test, second delivery): one question, the own team at once from the
 * federation's data, an example of the three things, then «Speichern» with an e-mail. The website
 * hands over ?q= (team name), ?farbe= and ?lang= (the language is set by the middleware); what it
 * already asked is not asked again.
 */
export function EntryView() {
  const t = useTranslations("entry");
  const params = useSearchParams();
  const router = useRouter();
  const club = Number(params.get("club")) || null;
  const team = Number(params.get("team")) || null;
  const step = params.get("step");
  const name = params.get("name");
  const [colour, setColour] = useState(FARBE[params.get("farbe") ?? ""] ?? SHIRTS[0][1]);
  const go = (next: Record<string, string | null>) => {
    const u = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(next)) (v == null ? u.delete(k) : u.set(k, v));
    u.set("farbe", WORD_OF[colour] ?? "blau");
    router.push(`/einstieg?${u.toString()}`);
  };
  if (step === "mail" && (team || name)) return <SaveStep club={club} team={team} name={name} colour={colour} onBack={() => go({ step: null })} />;
  if (club && team) return <TeamStep club={club} team={team} colour={colour} onColour={setColour} onSave={() => go({ step: "mail" })} onBack={() => go({ club: null, team: null })} />;
  return <SearchStep initial={params.get("q") ?? ""} onPick={(h, q) => go({ club: String(h.club.id), team: String(h.official_id), q })} onName={(n) => go({ name: n, step: "mail", q: null })} />;
}

function SearchStep({ initial, onPick, onName }: { initial: string; onPick: (h: Hit, q: string) => void; onName: (name: string) => void }) {
  const t = useTranslations("entry");
  const [text, setText] = useState(initial);
  const [q, setQ] = useState(initial.trim().length >= 3 ? initial.trim() : "");
  const [byName, setByName] = useState(false);
  const hits = useQuery({
    queryKey: ["public-teams", q],
    enabled: q.length >= 3,
    retry: false,
    queryFn: async () => {
      const r = await api.GET("/v1/public/teams", { params: { query: { q } } });
      if (r.error) throw r.error;
      return r.data ?? [];
    },
  });
  return (
    <section className="mx-auto max-w-2xl space-y-6" data-testid="entry-search">
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setQ(text.trim());
        }}
        className="space-y-3"
      >
        <label htmlFor="entry-q" className="font-slant block text-[34px] leading-tight md:text-[44px]">
          {t("ask")}
        </label>
        <div className="flex gap-2">
          <input
            id="entry-q"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t("placeholder")}
            autoComplete="off"
            autoFocus={!initial}
            aria-describedby="entry-q-hint"
            className="min-h-14 min-w-0 flex-1 border-2 border-ink bg-transparent px-4 text-[19px]"
          />
          <button type="submit" className={buttonClass("primary", "lg")}>
            {t("search")}
          </button>
        </div>
        <p id="entry-q-hint" className="m-0 text-[15px] text-ink-2">
          {t("short")}
        </p>
      </form>
      {hits.isFetching && <p className="text-[17px] text-ink-2" aria-busy="true">…</p>}
      {hits.error && <p className="text-[17px]">{t("unavailable")}</p>}
      {hits.data && hits.data.length === 0 && <p className="text-[17px]">{t("none", { q })}</p>}
      {hits.data && hits.data.length > 0 && (
        <ul className="m-0 list-none border-t-2 border-ink p-0" data-testid="entry-hits">
          {hits.data.map((h) => (
            <li key={h.official_id} className="border-b border-rule">
              <button type="button" onClick={() => onPick(h, q)} className="flex min-h-16 w-full cursor-pointer items-center justify-between gap-4 border-0 bg-transparent py-3 text-left">
                <span className="min-w-0">
                  <span className="block text-[19px] font-bold">{h.name}</span>
                  <span className="block text-[15px] text-ink-2">
                    {[h.league, h.club.city].filter(Boolean).join(" · ")}
                    {h.in_app && ` · ${t("inApp")}`}
                  </span>
                </span>
                <span aria-hidden className="font-slant text-2xl">
                  →
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {(hits.data || hits.error) && (
        <div className="space-y-3 border-t border-rule pt-5">
          {byName ? (
            <form
              onSubmit={(e: FormEvent<HTMLFormElement>) => {
                e.preventDefault();
                const n = String(new FormData(e.currentTarget).get("team") ?? "").trim();
                if (n) onName(n);
              }}
              className="flex flex-wrap items-end gap-2"
            >
              <label className="min-w-0 flex-1">
                <span className="mb-1 block text-[15px] font-semibold">{t("teamName")}</span>
                <input name="team" required maxLength={120} defaultValue={q} className="min-h-12 w-full border-2 border-ink bg-transparent px-3 text-[17px]" />
              </label>
              <button type="submit" className={buttonClass("secondary", "lg")}>
                {t("next")}
              </button>
            </form>
          ) : (
            <p className="m-0 text-[17px]">
              {t("noneWay")}{" "}
              <button type="button" onClick={() => setByName(true)} className="min-h-11 cursor-pointer border-0 bg-transparent p-0 font-bold underline decoration-2 underline-offset-4" data-testid="entry-by-name">
                {t("byName")}
              </button>
            </p>
          )}
        </div>
      )}
      <p className="text-[15px]">
        {t("haveAccount")}{" "}
        <Link href="/login" className="font-bold text-ink underline decoration-[1.5px] underline-offset-4">
          {t("login")}
        </Link>
      </p>
    </section>
  );
}

function TeamStep({ club, team, colour, onColour, onSave, onBack }: { club: number; team: number; colour: string; onColour: (c: string) => void; onSave: () => void; onBack: () => void }) {
  const t = useTranslations("entry");
  const tc = useTranslations("onboarding");
  const format = useFormatter();
  const q = useQuery({
    queryKey: ["public-team", club, team],
    retry: false,
    queryFn: async () => {
      const r = await api.GET("/v1/public/clubs/{club_id}/teams/{official_id}", { params: { path: { club_id: club, official_id: team } } });
      if (r.error) throw r.error;
      return r.data as Preview;
    },
  });
  if (q.isLoading) return <p className="text-[17px] text-ink-2" aria-busy="true">…</p>;
  if (!q.data) {
    return (
      <div className="space-y-4">
        <p className="text-[17px]">{t("unavailable")}</p>
        <button type="button" className={buttonClass("secondary")} onClick={onBack}>
          {t("back")}
        </button>
      </div>
    );
  }
  const p = q.data;
  const last = p.last;
  const result = last && last.own != null && last.opp != null ? (last.own > last.opp ? "won" : last.own < last.opp ? "lost" : "draw") : null;
  const run = p.run && p.run.count >= 2 ? t(p.run.result === "w" ? "runW" : p.run.result === "l" ? "runL" : "runD", { n: p.run.count }) : null;
  return (
    <div className="space-y-10" style={clubStyle(colour, SECOND(colour)) as CSSProperties} data-testid="entry-team">
      <div className="bleed-x -mt-6 sm:-mt-10">
        <WurfHead
          kick={last ? `${t("lastResult")} · ${t("vs", { opponent: last.opponent })} · ${format.dateTime(new Date(last.kickoff_at), { day: "numeric", month: "long" })}` : p.season}
          title={
            <>
              {p.name}
              <span className="block text-[0.55em]">{[p.rank != null ? t("rank", { rank: p.rank }) : null, run].filter(Boolean).join(" ")}</span>
            </>
          }
          own={last?.own ?? null}
          opp={last?.opp ?? null}
          ownName={p.name}
          oppName={last?.opponent ?? ""}
          waiting={!result}
        />
      </div>
      <fieldset className="m-0 border-0 p-0">
        <legend className="mb-2 text-[17px] font-bold">{t("colour")}</legend>
        <div className="flex flex-wrap gap-2.5">
          {SHIRTS.map(([key, hex]) => (
            <label key={key} className={cn("grid size-12 cursor-pointer place-items-center border-2", colour === hex ? "border-ink outline-3 outline-offset-2 outline-ink" : "border-rule")} style={{ background: hex }}>
              <input type="radio" name="shirt" className="sr-only" checked={colour === hex} onChange={() => onColour(hex)} aria-label={tc(`shirt.${key}` as "shirt.blue")} />
            </label>
          ))}
        </div>
        <p className="mt-2 mb-0 text-[15px] text-ink-2">{t("colourHint")}</p>
      </fieldset>
      {/* the one action right where the coach has seen his team; again at the end */}
      <button type="button" className={buttonClass("primary", "lg")} onClick={onSave}>
        {t("save")}
      </button>
      <TeamFacts p={p} />
      <p className="text-[15px] text-ink-2">{t("source")}</p>
      <Example />
      <div className="space-y-2 border-t-2 border-ink pt-5">
        <div className="flex flex-wrap items-center gap-4">
          <button type="button" className={buttonClass("primary", "lg")} onClick={onSave} data-testid="entry-save">
            {t("save")}
          </button>
          <button type="button" className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[17px] font-bold underline decoration-[1.5px] underline-offset-4" onClick={onBack}>
            {t("back")}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Table excerpt, scorers and next game of a team from the federation's data (also on Spiele
 * before the first video, UX test H02). */
export function TeamFacts({ p }: { p: Preview }) {
  const t = useTranslations("entry");
  const format = useFormatter();
  const ownRow = p.table.findIndex((r) => r.own);
  const rows = ownRow < 0 ? p.table.slice(0, 5) : p.table.slice(Math.max(0, ownRow - 2), ownRow + 3);
  return (
      <div className="grid gap-10 md:grid-cols-2">
      {rows.length > 0 && (
        <section>
          <SectionHead title={t("table")} note={p.group_name ?? p.league ?? undefined} />
          <table className="w-full border-collapse text-[17px]" data-testid="entry-table">
            <thead>
              <tr className="border-b-2 border-ink text-[15px] text-ink-2">
                <th scope="col" className="py-1.5 text-left font-semibold" />
                <th scope="col" className="py-1.5 text-left font-semibold" />
                <th scope="col" className="py-1.5 text-right font-semibold">{t("games")}</th>
                <th scope="col" className="py-1.5 text-right font-semibold">{t("diff")}</th>
                <th scope="col" className="py-1.5 text-right font-semibold">{t("points")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.rank}-${r.name}`} className={cn("border-b border-rule", r.own && "font-bold")}>
                  <td className="py-2 pr-2 tabular-nums">{r.rank}</td>
                  <td className="py-2">{r.name}</td>
                  <td className="py-2 text-right tabular-nums">{r.games}</td>
                  <td className="py-2 text-right tabular-nums">{r.goal_difference}</td>
                  <td className="py-2 text-right tabular-nums">{r.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <div className="space-y-10">
        {p.scorers.length > 0 && (
          <section>
            <SectionHead title={t("scorers")} note={t("scorersBasis", { n: p.scorer_games })} />
            <ol className="m-0 list-none p-0" data-testid="entry-scorers">
              {p.scorers.map((s) => (
                <li key={s.name} className="flex justify-between border-b border-rule py-2 text-[17px]">
                  <span>{s.name}</span>
                  <b className="tabular-nums">{s.goals}</b>
                </li>
              ))}
            </ol>
          </section>
        )}
        {p.next && (
          <section>
            <SectionHead title={t("nextGame")} />
            <p className="m-0 text-[19px] font-bold">{p.next.opponent}</p>
            <p className="m-0 text-[17px] text-ink-2">
              {format.dateTime(new Date(p.next.kickoff_at), { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })} · {p.next.home ? t("home") : t("away")}
            </p>
          </section>
        )}
      </div>
    </div>
  );
}

/** «Rang 5. Vier Siege in Folge.» from the preview, or null. */
export function useStanding(p: Preview | null | undefined): string | null {
  const t = useTranslations("entry");
  if (!p) return null;
  const run = p.run && p.run.count >= 2 ? t(p.run.result === "w" ? "runW" : p.run.result === "l" ? "runL" : "runD", { n: p.run.count }) : null;
  return [p.rank != null ? `${t("rank", { rank: p.rank })}.` : null, run].filter(Boolean).join(" ") || null;
}

/** The three things of a demo match, clearly an example (the website promises it). */
function Example() {
  const t = useTranslations("entry");
  const ta = useTranslations("anlauf");
  const text = useThingText();
  const g = useQuery({
    queryKey: ["example-graphics"],
    staleTime: Infinity,
    queryFn: async () => (await (await fetch("/example/graphics.json")).json()) as MatchGraphics,
  });
  const things = g.data ? threeThings(goalRuns(g.data)) : [];
  if (things.length === 0) return null;
  return (
    <section data-testid="entry-example" aria-labelledby="entry-example-title">
      <SectionHead title={<span id="entry-example-title">{t("example")}</span>} note={t("exampleNote")} />
      <ol className="m-0 grid list-none grid-cols-1 gap-8 p-0 md:grid-cols-3">
        {things.map((x, i) => (
          <li key={x.key} className="space-y-2">
            <p className="m-0 font-mono text-[15px] font-bold text-ink-2">{ta("index", { n: i + 1, total: things.length })}</p>
            <p className="m-0 flex items-baseline gap-2">
              <b className="font-num text-[56px] leading-[.8]">{x.value}</b>
              <span className="font-slant text-[19px] text-ink-2">{x.key === "conceded_fast_breaks" ? ta("unitFastBreaks") : ta("unitOf", { of: x.of ?? 0 })}</span>
            </p>
            <h3 className="m-0 text-[19px] font-bold">{text(x)}</h3>
            <Bundle goals={x.goals} rest={x.rest} width={300} label={text(x)} />
          </li>
        ))}
      </ol>
    </section>
  );
}

function SaveStep({ club, team, name, colour, onBack }: { club: number | null; team: number | null; name: string | null; colour: string; onBack: () => void }) {
  const t = useTranslations("entry");
  const locale = useLocale();
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const farbe = WORD_OF[colour] ?? "blau";
  const next = team && club ? `/einstieg/speichern?club=${club}&team=${team}&farbe=${farbe}` : `/einstieg/speichern?name=${encodeURIComponent(name ?? "")}&farbe=${farbe}`;
  const legal = (page: string) => `https://handball-ai.ch${locale === "de-CH" ? "" : `/${locale}`}/${page}`;
  async function send(email: string) {
    setBusy(true);
    const r = await api.POST("/v1/auth/start", { body: { email, locale: (["de-CH", "fr", "en"].includes(locale) ? locale : "de-CH") as "de-CH", next } });
    setBusy(false);
    if (r.error) return setError(t("needEmail"));
    setSent(email);
  }
  useEffect(() => setError(null), [sent]);
  if (sent) {
    return (
      <section className="mx-auto max-w-xl space-y-4" role="status" data-testid="entry-sent">
        <h1 className="font-slant text-[34px] leading-tight md:text-[44px]">{t("sent")}</h1>
        <p className="text-[17px]">{t("sentText", { email: sent })}</p>
        <button type="button" className={buttonClass("secondary")} disabled={busy} onClick={() => void send(sent)}>
          {t("resend")}
        </button>
      </section>
    );
  }
  return (
    <form
      className="mx-auto max-w-xl space-y-5"
      data-testid="entry-mail"
      noValidate
      onSubmit={(e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const email = String(new FormData(e.currentTarget).get("email") ?? "").trim();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError(t("needEmail"));
        void send(email);
      }}
    >
      <h1 className="font-slant text-[34px] leading-tight md:text-[44px]">{t("emailTitle")}</h1>
      <label className="block">
        <span className="mb-1 block text-[17px] font-bold">{t("email")}</span>
        <input name="email" type="email" autoComplete="email" inputMode="email" required aria-invalid={error ? true : undefined} aria-describedby="entry-mail-hint" className="min-h-14 w-full border-2 border-ink bg-transparent px-4 text-[19px]" />
      </label>
      {error && (
        <p className="m-0 text-[17px] font-bold text-error" role="alert">
          {error}
        </p>
      )}
      <p id="entry-mail-hint" className="m-0 text-[17px] text-ink-2">
        {t("emailHint")}
      </p>
      <p className="m-0 text-[17px] font-bold">{t("trial")}</p>
      <button type="submit" className={buttonClass("primary", "lg")} disabled={busy} data-testid="entry-send">
        {t("send")}
      </button>
      <p className="m-0 text-[15px] text-ink-2">
        {t.rich("terms", {
          terms: (c) => (
            <a href={legal("agb")} target="_blank" rel="noreferrer" className="font-semibold text-ink underline underline-offset-4">
              {c}
            </a>
          ),
          privacy: (c) => (
            <a href={legal("datenschutz")} target="_blank" rel="noreferrer" className="font-semibold text-ink underline underline-offset-4">
              {c}
            </a>
          ),
        })}
      </p>
      <button type="button" className="min-h-11 cursor-pointer border-0 bg-transparent p-0 text-[17px] font-bold underline decoration-[1.5px] underline-offset-4" onClick={onBack}>
        {t("back")}
      </button>
    </form>
  );
}

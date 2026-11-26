import type { Schemas } from "@handball/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import deCH from "../../../../../../messages/de-CH.json";
import en from "../../../../../../messages/en.json";
import fr from "../../../../../../messages/fr.json";
import { KnownFacts } from "./known-facts";

// While a long analysis runs: what the coach can use meanwhile, offered where the wait is
// (honest waiting): the video once it plays, the shirt numbers that are missing. Invented match.
const match = {
  id: "m1",
  team_id: "t1",
  kind: "match",
  kickoff_at: "2026-11-21T17:00:00Z",
  opponent: { id: "op1", name: "TV Seewald" },
  official_game: null,
} as unknown as Schemas["MatchOut"];

function render(props: Partial<ComponentProps<typeof KnownFacts>> = {}, messages: Record<string, unknown> = deCH, locale = "de-CH"): string {
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client: new QueryClient() },
      createElement(
        NextIntlClientProvider,
        { locale, messages, timeZone: "Europe/Zurich", now: new Date("2026-11-21T19:00:00Z") } as ComponentProps<typeof NextIntlClientProvider>,
        createElement(KnownFacts, { orgId: "o", match, ownName: "HC Muster", oppName: "TV Seewald", stats: null, names: {}, hasReport: false, checks: 0, staff: true, ...props }),
      ),
    ),
  );
}

const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

describe("meanwhile: what can be used while the analysis runs", () => {
  it("offers the video once it plays and names the missing shirt numbers", () => {
    const html = render({ onWatch: vi.fn(), withoutNumber: 3 });
    expect(html).toContain('data-testid="meanwhile-watch"');
    expect(text(html)).toContain("das Video schon ansehen");
    expect(text(html)).toContain("Rückennummern ergänzen: 3 Spieler haben noch keine");
  });

  it("offers neither before the video plays nor numbers when all have one", () => {
    const html = render({ withoutNumber: 0 });
    expect(html).not.toContain("meanwhile-watch");
    expect(text(html)).toContain("den Kader prüfen");
  });

  it("offers nothing to do to whoever does not work with the match", () => {
    expect(render({ staff: false, onWatch: vi.fn(), withoutNumber: 2 })).not.toContain('data-testid="meanwhile"');
  });

  it("has the words in French and English", () => {
    expect(text(render({ onWatch: vi.fn(), withoutNumber: 1 }, fr, "fr"))).toContain("1 joueur n");
    expect(text(render({ onWatch: vi.fn(), withoutNumber: 2 }, en, "en"))).toContain("2 players have none yet");
  });
});

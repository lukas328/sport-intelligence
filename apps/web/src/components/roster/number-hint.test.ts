import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../../messages/de-CH.json";
import en from "../../../messages/en.json";
import fr from "../../../messages/fr.json";
import { RosterNumberHint } from "./number-hint";
import { QuickRoster } from "./quick-roster";

// Audit #160: names come from shirt numbers. Before the upload and in the people step the coach
// is told who has no number and which number two players share, with the way to fix it.
// Invented players.
const e = (n: number | null, first: string, last: string, active = true) => ({ jersey_number: n, first_name: first, last_name: last, active, player_id: first });

function wrap(node: ReturnType<typeof createElement>, roster: unknown[] | null, messages: Record<string, unknown> = deCH, locale = "de-CH"): string {
  const client = new QueryClient();
  if (roster) client.setQueryData(["roster", "s1"], roster);
  return renderToStaticMarkup(
    createElement(QueryClientProvider, { client }, createElement(NextIntlClientProvider, { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>, node)),
  );
}
const hint = (roster: unknown[], messages?: Record<string, unknown>, locale?: string) =>
  wrap(createElement(RosterNumberHint, { orgId: "o", teamId: "t1", seasonId: "s1" }), roster, messages, locale);
const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

describe("roster number hint", () => {
  it("names the players without a number and the number two share, with the way to fix it", () => {
    const html = hint([e(7, "Lena", "Muster"), e(null, "Mia", "Beispiel"), e(null, "Noa", "Probst"), e(9, "Ida", "Ruf"), e(9, "Zoe", "Wald"), e(null, "Old", "Gone", false)]);
    expect(text(html)).toContain("2 Spieler ohne Rückennummer, Namen kann die Analyse nicht automatisch zuordnen: Mia Beispiel, Noa Probst");
    expect(text(html)).toContain("Nr. 9 ist doppelt vergeben: Ida Ruf, Zoe Wald");
    expect(text(html)).not.toContain("Old Gone"); // a player no longer in the squad does not count
    expect(html).toContain('href="/app/o/teams/t1?edit=1"');
    expect(text(html)).toContain("Rückennummern ergänzen");
  });

  it("asks for a squad when there is none, and says nothing for a complete one", () => {
    const none = hint([]);
    expect(text(none)).toContain("Noch kein Kader.");
    expect(text(none)).toContain("Kader erfassen");
    expect(hint([e(1, "A", "B"), e(2, "C", "D")])).toBe("");
  });

  it("speaks French and English", () => {
    const roster = [e(null, "Mia", "Beispiel")];
    expect(text(hint(roster, fr, "fr"))).toContain("1 joueur sans numéro de maillot");
    expect(text(hint(roster, en, "en"))).toContain("1 player without a shirt number");
  });
});

describe("quick roster entry", () => {
  it("is a text field for number and name per line, typed or pasted", () => {
    const html = wrap(createElement(QuickRoster, { path: { org_id: "o", team_id: "t1", season_id: "s1" }, onImported: () => {} }), null);
    expect(html).toContain('data-testid="quick-roster-text"');
    expect(text(html)).toContain("Nummer und Name, ein Spieler pro Zeile");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*data-testid="quick-roster-save"|data-testid="quick-roster-save"[^>]*disabled=""/);
  });
});

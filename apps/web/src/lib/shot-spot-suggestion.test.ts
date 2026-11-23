import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import deCH from "../../messages/de-CH.json";
import en from "../../messages/en.json";
import fr from "../../messages/fr.json";
import { ShotSpotPicker } from "@/components/anlauf/shot-spot-picker";
import { spotSuggestion, tapAnswer } from "./shot-spot";

// A22: «Von wo?» preselects the estimate from the tracks as a suggestion; one tap on it confirms
// it (the zone alone: the API takes the estimated point over as the coach's), a tap elsewhere sets
// another place. An unconfirmed estimate never counts as the coach's.

describe("the estimate as a suggestion", () => {
  it("offers an estimated place on the court, never the coach's own nor a kind", () => {
    expect(spotSuggestion({ zone: "rl", zone_source: "estimated", spot_by_coach: false })).toBe("rl");
    // «Weiss nicht» with an estimate behind it: still offered
    expect(spotSuggestion({ zone: "ra", zone_source: "unknown", spot_by_coach: false })).toBe("ra");
    // the coach's place reads «Bisher», not «Vorschlag»
    expect(spotSuggestion({ zone: "rl", zone_source: "coach", spot_by_coach: true })).toBeNull();
    // a reviewed candidate only carries zone_source
    expect(spotSuggestion({ zone: "kr", zone_source: "estimated" })).toBe("kr");
    expect(spotSuggestion({ zone: "kr", zone_source: "coach" })).toBeNull();
    // Siebenmeter and Gegenstoss are never estimated places
    expect(spotSuggestion({ zone: "m7", zone_source: "estimated", spot_by_coach: false })).toBeNull();
    expect(spotSuggestion({ zone: null, zone_source: null, spot_by_coach: false })).toBeNull();
  });

  it("a tap on the suggestion confirms it with the zone alone, elsewhere it keeps the tapped point", () => {
    expect(tapAnswer("rl", "rl", [34, 15])).toEqual({ answer: "rl" });
    expect(tapAnswer("kr", "rl", [35.5, 10.5])).toEqual({ answer: "kr", point: [35.5, 10.5] });
    // without a suggestion a tap is as before
    expect(tapAnswer("rm", null, [30, 10])).toEqual({ answer: "rm", point: [30, 10] });
    // a key (Enter) gives no point
    expect(tapAnswer("rm", null)).toEqual({ answer: "rm" });
  });
});

function render(props: Partial<ComponentProps<typeof ShotSpotPicker>>, messages: Record<string, unknown> = deCH, locale = "de-CH"): string {
  return renderToStaticMarkup(
    createElement(
      NextIntlClientProvider,
      { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>,
      createElement(ShotSpotPicker, { onPick: () => {}, ...props }),
    ),
  );
}

const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/\s+/g, " ");

describe("«Von wo?» with a suggestion", () => {
  it("marks the estimated place as «Vorschlag» and says how to confirm it", () => {
    const html = render({ suggested: "rl" });
    expect(html).toMatch(/data-testid="spot-zone-rl"[^>]*data-suggested="true"/);
    expect(html).toContain('aria-label="Rückraum links, Vorschlag"');
    expect((html.match(/data-suggested/g) ?? []).length).toBe(1);
    expect(text(html)).toContain("Die App schlägt vor: Rückraum links. Tippe darauf, um zu bestätigen");
  });

  it("names it in French and English too", () => {
    expect(text(render({ suggested: "ra" }, fr, "fr"))).toContain("L'app propose : Aile droite.");
    expect(text(render({ suggested: "ra" }, en, "en"))).toContain("The app suggests: Right wing.");
  });

  it("shows no suggestion next to the coach's own answer, and none without an estimate", () => {
    const own = render({ current: "kr", suggested: "rl" });
    expect(own).not.toContain("data-suggested");
    expect(own).not.toContain('data-testid="spot-suggestion-note"');
    expect(own).toContain('aria-label="Kreis, Bisher"');
    const none = render({});
    expect(none).not.toContain("data-suggested");
    expect(none).not.toContain("Vorschlag");
  });
});

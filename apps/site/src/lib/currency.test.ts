import plans from "@handball/plans";
import { describe, expect, it } from "vitest";
import de from "@/messages/de";
import en from "@/messages/en";
import fr from "@/messages/fr";
import { currencyOf, perTeam } from "./currency";

describe("prices in EUR and CHF (europa.md EU3)", () => {
  it("picks CHF for a Swiss browser language, EUR for the rest, and a link's ?cur= first", () => {
    expect(currencyOf(["de-CH", "de"])).toBe("CHF");
    expect(currencyOf(["fr-CH"])).toBe("CHF");
    expect(currencyOf(["de-DE", "en"])).toBe("EUR");
    expect(currencyOf(["fr-FR"])).toBe("EUR");
    expect(currencyOf(["de-CH"], "eur")).toBe("EUR");
    expect(currencyOf(["en"], "chf")).toBe("CHF");
  });

  it("a team in the club plan costs the club price divided by its teams (199 for 10: 19.90)", () => {
    const club = plans.plans.find((p) => p.plan === "club")!;
    expect(perTeam(club)).toBe((club.price_chf_month / club.teams).toFixed(2));
  });

  it("no price text names one currency alone, and none promises card payment", () => {
    for (const m of [de, fr, en]) {
      for (const s of [m.home.priceTitle, m.home.priceText, m.pricing.lead, m.pricing.perMonth, m.pricing.perYear, ...m.pricing.path.map((p) => p.title + p.text)]) {
        expect(s).not.toMatch(/\bCHF\b(?! oder| or| ou|\/)/);
      }
      expect(JSON.stringify(m.pricing.faq)).not.toMatch(/Karte|card|carte/i);
    }
  });
});

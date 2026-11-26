import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import { createElement, type ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import deCH from "../../../messages/de-CH.json";
import en from "../../../messages/en.json";
import fr from "../../../messages/fr.json";
import { BillingSection } from "./billing-section";

// A club abroad pays in EUR; while no EUR price is set up (Q-BILL-EU5) the page says so and
// offers no checkout, instead of one that fails or bills in francs.
const plan = (p: string, price: number) => ({ plan: p, price_month: price, teams: 1, matches_per_season: null, storage_gb: 10, gpu_minutes_month: null, features: [], trial_days: 0 });
const billing = (extra: Record<string, unknown>) => ({
  plan: "free",
  effective_plan: "free",
  status: null,
  trial_ends_at: null,
  current_period_end: null,
  paid_until: null,
  enforced: true,
  limits: { teams: 1, matches_per_season: 2, storage_gb: 10, gpu_minutes_month: null },
  features: [],
  usage: { teams: 1, max_matches_per_season: 0, storage_bytes: 0, gpu_minutes: 0 },
  plans: [plan("free", 0), plan("team", 39), plan("club", 199)],
  ...extra,
});

function render(b: Record<string, unknown>, messages: Record<string, unknown> = deCH, locale = "de-CH"): string {
  const client = new QueryClient();
  client.setQueryData(["billing", "o"], b);
  client.setQueryData(["invoice-price", "o"], null);
  return renderToStaticMarkup(
    createElement(
      QueryClientProvider,
      { client },
      createElement(NextIntlClientProvider, { locale, messages, timeZone: "Europe/Zurich" } as ComponentProps<typeof NextIntlClientProvider>, createElement(BillingSection, { orgId: "o" })),
    ),
  );
}

describe("billing: no checkout in a currency without prices", () => {
  it("says online payment in EUR is not open yet, and the plan buttons are off", () => {
    const html = render(billing({ currency: "EUR", checkout_available: false, checkout_unavailable: "currency" }));
    expect(html).toContain('data-testid="billing-unavailable-currency"');
    expect(html).toContain("Online-Zahlung in EUR ist noch nicht freigeschaltet.");
    expect(html).toContain("EUR 39 pro Monat"); // the same number, shown honestly
    expect(html.match(/<button[^>]*disabled=""[^>]*>Team wählen/g) ?? html.match(/disabled=""/g)).toBeTruthy();
  });

  it("keeps the plain sentence when Stripe is not set up at all, and nothing when it is", () => {
    const off = render(billing({ currency: "CHF", checkout_available: false, checkout_unavailable: "not_configured" }));
    expect(off).toContain("Online-Zahlung ist noch nicht eingerichtet.");
    expect(off).not.toContain("billing-unavailable-currency");
    const on = render(billing({ currency: "CHF", checkout_available: true, checkout_unavailable: null }));
    expect(on).not.toContain("noch nicht");
  });

  it("speaks French and English", () => {
    const b = billing({ currency: "EUR", checkout_available: false, checkout_unavailable: "currency" });
    expect(render(b, fr, "fr")).toContain("Le paiement en ligne en EUR");
    expect(render(b, en, "en")).toContain("Online payment in EUR is not open yet.");
  });
});

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import de from "@/messages/de";
import en from "@/messages/en";
import fr from "@/messages/fr";
import plans from "@handball/plans";

function leaves(value: unknown, path = ""): [string, string][] {
  if (typeof value === "string") return [[path, value]];
  if (Array.isArray(value)) return value.flatMap((v, i) => leaves(v, `${path}[${i}]`));
  return Object.entries(value as Record<string, unknown>).flatMap(([k, v]) => leaves(v, path ? `${path}.${k}` : k));
}

describe("site messages", () => {
  const ref = leaves(de);
  it.each([["fr", fr], ["en", en]])("%s has the same keys and placeholders as de", (_, other) => {
    const map = new Map(leaves(other));
    expect([...map.keys()]).toEqual(ref.map(([k]) => k));
    for (const [k, v] of ref) {
      const ph = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
      expect(ph(map.get(k) ?? ""), k).toEqual(ph(v));
    }
  });

  it("says scène in French, like the app (one word per thing), never séquence", () => {
    const dir = join(__dirname, "..", "..", "content");
    const texts: [string, string][] = leaves(fr);
    for (const kind of ["ratgeber", "help", "blog"]) {
      for (const f of readdirSync(join(dir, kind, "fr"))) texts.push([`${kind}/fr/${f}`, readFileSync(join(dir, kind, "fr", f), "utf8")]);
      texts.push([`${kind}/index.ts`, readFileSync(join(dir, kind, "index.ts"), "utf8")]);
    }
    for (const [k, v] of texts) expect(v.normalize("NFC"), k).not.toMatch(/(?<!con)s\u00e9quence/i);
  });

  // «Fragen» in the Ratgeber's frame (BEFUNDE-3 U8): every question sits in one of the four themes,
  // each theme holds at least one; the open-up line is the label of «So hilft …:» without its colon
  it("groups the questions on «Fragen» by theme", () => {
    for (const msgs of [de, fr, en]) {
      const themes = Object.keys(msgs.faq.groups);
      expect(themes).toEqual(["filmen", "analyse", "team", "preise"]);
      for (const q of msgs.faq.items) expect(themes, q.q).toContain(q.g);
      for (const g of themes) expect(msgs.faq.items.some((q) => q.g === g), g).toBe(true);
      expect(msgs.faq.hiLabel.startsWith(msgs.faq.more)).toBe(true);
    }
    expect(fr.faq.items.map((q) => q.g)).toEqual(de.faq.items.map((q) => q.g));
    expect(en.faq.items.map((q) => q.g)).toEqual(de.faq.items.map((q) => q.g));
  });

  it("puts the filming page in five short rules, with panning allowed", () => {
    for (const msgs of [de, fr, en]) {
      expect(msgs.filming.rules).toHaveLength(5);
      for (const r of msgs.filming.rules) expect(r.text.length, r.title).toBeLessThanOrEqual(80);
    }
    expect(de.filming.rules.map((r) => r.title)).toEqual(["Handy oder Kamera", "Hoch an die Mittellinie", "Beide Tore im Bild", "Fest ist am besten", "Schwenken geht"]);
  });

  // Europe (L14, EU4): for clubs across Europe; «Entwickelt in der Schweiz» in the footer and on
  // «Über uns» only, and the team search says honestly that it covers teams in Switzerland.
  it("positions for clubs across Europe, with the Swiss mark only in the footer and on Über uns", () => {
    const swiss = /Schweiz|Suisse|Switzerland|Swiss/;
    for (const msgs of [de, fr, en]) {
      for (const [k, v] of leaves({ meta: msgs.meta, kick: msgs.home.kick, title: msgs.home.title, lead: msgs.home.lead, trustTitle: msgs.home.trustTitle, homeText: msgs.us.homeText, us: msgs.us.head, usLead: msgs.us.lead, usMeta: msgs.us.description })) {
        expect(v, k).not.toMatch(swiss);
      }
      expect(msgs.footer.made).toMatch(swiss);
      expect(msgs.us.sections.map((s) => s.title)).toContain(msgs.footer.made);
      expect(msgs.home.teamAfter).toMatch(swiss);
    }
    expect(de.home.trust.map((t) => t.title)).toContain("DSGVO und Schweizer DSG");
    expect(fr.home.trust.map((t) => t.title)).toContain("RGPD et LPD suisse");
    expect(en.home.trust.map((t) => t.title)).toContain("GDPR and Swiss FADP");
  });

  // U17: the team search on the website and its next step in the app (/einstieg) use the same
  // words: the question, the button, the hint under the field and the sentence on what it covers
  it("words the team search like the app's entry", () => {
    for (const [lang, msgs] of [["de-CH", de], ["fr", fr], ["en", en]] as const) {
      const app = JSON.parse(readFileSync(join(__dirname, "..", "..", "..", "web", "messages", `${lang}.json`), "utf8")).entry;
      expect(msgs.home.teamLabel, lang).toBe(app.ask);
      expect(msgs.home.teamButton, lang).toBe(app.search);
      expect(msgs.home.teamHint, lang).toBe(app.short);
      expect(msgs.home.teamAfter.endsWith(app.scope), lang).toBe(true);
    }
  });

  it("uses no long dashes and no sharp s", () => {
    for (const msgs of [de, fr, en]) for (const [k, v] of leaves(msgs)) expect(v, k).not.toMatch(/[–—]/);
    for (const [k, v] of ref) expect(v, k).not.toContain("ß");
  });

  // U23, A9: the prices compare the plans feature by feature; the goalkeeper figures are in Team
  // and Verein without an add-on (not in Gratis, 18.11.2026), so no add-on price appears anywhere
  it("names every plan feature on the prices page and never prices a goalkeeper add-on", () => {
    const features = new Set(plans.plans.flatMap((p) => p.features as string[]));
    features.delete("tracking"); // the row «Automatische Analyse»
    for (const f of features) if (f.startsWith("goalkeeper")) features.delete(f); // the row «Torhüter»
    for (const msgs of [de, fr, en]) {
      expect(Object.keys(msgs.pricing.featureNames).sort()).toEqual([...features].sort());
      expect(msgs.pricing.featureNames.priority).toMatch(/Support|support/);
      for (const [k, v] of leaves(msgs)) expect(v, k).not.toMatch(/Torhüter-Modul|module gardien|goalkeeper add-on|CHF 7\b/i);
    }
    expect(de.pricing.perYear).toContain("{gift} Monate geschenkt");
  });

  // Lukas, 18.11.2026: the goalkeeper module only from Team on, the row «Torhüter» says so
  it("ticks the goalkeepers for Team and Verein only and promises them to no free plan", () => {
    const has = (plan: string) => (plans.plans.find((p) => p.plan === plan)!.features as string[]).includes("goalkeepers");
    expect([has("free"), has("team"), has("club")]).toEqual([false, true, true]);
    for (const msgs of [de, fr, en]) expect(msgs.pricing.goalkeepersSub).not.toMatch(/jedem Plan|für alle|every plan|for everyone|chaque|tous les/i);
  });
});

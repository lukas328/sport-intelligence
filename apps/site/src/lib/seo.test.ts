import { describe, expect, it } from "vitest";
import sitemap from "../app/sitemap";
import robots from "../app/robots";
import { GUIDES } from "../../content/ratgeber";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { alternates, ogImage, pageMeta } from "./seo";
import { llmsFullTxt, llmsTxt } from "./llms";

describe("search engines", () => {
  it("lists every page in every language, each with reciprocal alternates and x-default", () => {
    const map = sitemap();
    const urls = new Set(map.map((e) => e.url));
    for (const e of map) {
      const langs = e.alternates!.languages! as Record<string, string>;
      expect(langs["x-default"]).toBeTruthy();
      expect(Object.values(langs)).toContain(e.url);
      for (const [code, url] of Object.entries(langs)) {
        if (code === "x-default") continue;
        expect(["de-CH", "fr-CH", "en"]).toContain(code);
        expect(urls.has(url), url).toBe(true);
      }
    }
    for (const g of GUIDES) for (const l of g.locales) expect(urls.has(`https://handball-intelligence.com/${l}/ratgeber/${g.slug}/`)).toBe(true);
  });

  it("gives German-only pages only de-CH and x-default", () => {
    expect(alternates("ratgeber/x", ["de"])).toEqual({ "de-CH": "https://handball-intelligence.com/de/ratgeber/x/", "x-default": "https://handball-intelligence.com/de/ratgeber/x/" });
  });

  it("gives every language its own link preview with the start page's tagline as alt text", () => {
    expect(ogImage("de")).toEqual({ url: "/og-de.png", width: 1200, height: 630, alt: "Handball Intelligence: Spielanalyse mit KI für Handballtrainerinnen und -trainer" });
    expect(ogImage("fr").alt).toBe("Handball Intelligence: Analyse de match avec IA pour les entraîneuses et entraîneurs de handball");
    expect(ogImage("en").alt).toBe("Handball Intelligence: Match analysis with AI for handball coaches");
    for (const l of ["de", "fr", "en"] as const) {
      expect(existsSync(join(__dirname, "../../public", `og-${l}.png`))).toBe(true);
      const m = pageMeta(l, "preise", "x", "y");
      expect(m.openGraph?.images).toEqual([ogImage(l)]);
      expect(m.twitter?.images).toEqual([ogImage(l)]);
    }
    expect(existsSync(join(__dirname, "../../public/og.png"))).toBe(true);
  });

  it("lets everyone crawl and names the sitemap", () => {
    const r = robots();
    const rules = Array.isArray(r.rules) ? r.rules : [r.rules];
    expect(rules.every((x) => x.allow === "/" && !x.disallow)).toBe(true);
    expect(r.sitemap).toBe("https://handball-intelligence.com/sitemap.xml");
  });

  it("writes llms.txt with the share of the work and the prices, without caveats (W32)", () => {
    const txt = llmsTxt();
    expect(txt.startsWith("# Handball Intelligence\n")).toBe(true);
    expect(txt).toContain("## Das machst du");
    // the effort as it is (W33): a few questions, the court once per hall, the throw spot if you like
    expect(txt).toContain("Ein paar Fragen beantworten, wo die Analyse unsicher ist: höchstens zehn pro Spiel");
    expect(txt).toContain("pro Halle und Kameraplatz nur einmal");
    expect(txt).toContain("Wenn du magst, nach einem Tor den vorgeschlagenen Wurfort mit einem Tipp bestätigen.");
    expect(txt).not.toMatch(/Tor für Tor|bei jedem Tor|freiwilligen Fragen/);
    expect(txt).toMatch(/Team: CHF oder EUR \d+ im Monat/);
    // for clubs across Europe, and honest about what the team search covers (L14)
    expect(txt).toContain("für Vereine in ganz Europa");
    expect(txt).toContain("Team und Spielplan: Für Teams aus der Schweiz");
    expect(txt).not.toMatch(/Wir kommen aus der Schweiz|zuerst in der Schweiz/);
    expect(txt).not.toMatch(/noch nicht|vorgesehen|geschätzt|vor dem öffentlichen Start/i);
    expect(llmsFullTxt().length).toBeGreaterThan(txt.length);
  });
});

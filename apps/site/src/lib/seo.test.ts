import { describe, expect, it } from "vitest";
import sitemap from "../app/sitemap";
import robots from "../app/robots";
import { GUIDES } from "../../content/ratgeber";
import { alternates } from "./seo";
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
    for (const g of GUIDES) for (const l of g.locales) expect(urls.has(`https://handball-ai.ch/${l}/ratgeber/${g.slug}/`)).toBe(true);
  });

  it("gives German-only pages only de-CH and x-default", () => {
    expect(alternates("ratgeber/x", ["de"])).toEqual({ "de-CH": "https://handball-ai.ch/de/ratgeber/x/", "x-default": "https://handball-ai.ch/de/ratgeber/x/" });
  });

  it("lets everyone crawl and names the sitemap", () => {
    const r = robots();
    const rules = Array.isArray(r.rules) ? r.rules : [r.rules];
    expect(rules.every((x) => x.allow === "/" && !x.disallow)).toBe(true);
    expect(r.sitemap).toBe("https://handball-ai.ch/sitemap.xml");
  });

  it("writes llms.txt with the limits and without a price as an offer", () => {
    const txt = llmsTxt();
    expect(txt.startsWith("# Handball Intelligence\n")).toBe(true);
    expect(txt).toContain("Den Ball verfolgen");
    expect(txt).toContain("noch nicht endgültig");
    expect(llmsFullTxt().length).toBeGreaterThan(txt.length);
  });
});

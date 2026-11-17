import { describe, expect, it } from "vitest";
import { DEFAULT_SITE_URL, sitePage } from "./site";

describe("the way back to the website (BEFUNDE-2 L5)", () => {
  it("leads to the website's start page in the visitor's language", () => {
    expect(sitePage("https://handball-intelligence.com", "de-CH")).toBe("https://handball-intelligence.com/de/");
    expect(sitePage("https://handball-intelligence.com", "fr")).toBe("https://handball-intelligence.com/fr/");
    expect(sitePage("https://handball-intelligence.com", "en")).toBe("https://handball-intelligence.com/en/");
  });

  it("falls back to the default site and to German, never to a path in the app", () => {
    expect(DEFAULT_SITE_URL).toMatch(/^https:\/\//);
    expect(sitePage(null, "de-CH")).toBe(`${DEFAULT_SITE_URL}/de/`);
    expect(sitePage("", "it")).toBe(`${DEFAULT_SITE_URL}/de/`);
  });
});

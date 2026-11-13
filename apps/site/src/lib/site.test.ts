import { describe, expect, it } from "vitest";
import { START_ACTION, startUrl } from "./site";

describe("links into the app", () => {
  it("leads to the team preview, with the team name and the language", () => {
    expect(START_ACTION).toBe("https://app.handball-ai.ch/einstieg");
    expect(startUrl("de-CH")).toBe("https://app.handball-ai.ch/einstieg?lang=de-CH");
    expect(startUrl("fr", "Pfadi Winterthur")).toBe("https://app.handball-ai.ch/einstieg?q=Pfadi%20Winterthur&lang=fr");
    expect(startUrl("de-CH", undefined, "gruen")).toBe("https://app.handball-ai.ch/einstieg?farbe=gruen&lang=de-CH");
  });
});

import { describe, expect, it } from "vitest";
import { START_ACTION, byHandUrl, startUrl } from "./site";

describe("links into the app", () => {
  it("leads to the team preview, with the team name and the language", () => {
    expect(START_ACTION).toBe("https://app.handball-intelligence.com/einstieg");
    expect(startUrl("de-CH")).toBe("https://app.handball-intelligence.com/einstieg?lang=de-CH");
    expect(startUrl("fr", "Handball Talstadt")).toBe("https://app.handball-intelligence.com/einstieg?q=Handball%20Talstadt&lang=fr");
    expect(startUrl("de-CH", undefined, "gruen")).toBe("https://app.handball-intelligence.com/einstieg?farbe=gruen&lang=de-CH");
  });

  it("leads teams outside the federation data straight to the way by hand", () => {
    expect(byHandUrl("de-CH")).toBe("https://app.handball-intelligence.com/einstieg?step=name&lang=de-CH");
    expect(byHandUrl("fr", "rot")).toBe("https://app.handball-intelligence.com/einstieg?step=name&farbe=rot&lang=fr");
  });
});

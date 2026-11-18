import { describe, expect, it } from "vitest";
import { HELP } from "../../content/help";
import { matchesAll, normalise, searchHelp } from "./search";

describe("help search", () => {
  it("normalises umlauts and accents", () => {
    expect(normalise("Präsentation")).toBe("praesentation");
    expect(normalise("Révocation")).toBe("revocation");
  });

  it("finds articles by title, keyword and summary in each language", () => {
    expect(searchHelp(HELP, "de", "Rechnung")[0]?.slug).toBe("abo-und-rechnung");
    expect(searchHelp(HELP, "de", "praesentation")[0]?.slug).toBe("praesentation");
    expect(searchHelp(HELP, "fr", "consentement")[0]?.slug).toBe("einwilligungen");
    expect(searchHelp(HELP, "en", "tripod")[0]?.slug).toBe("aufnahme");
    expect(searchHelp(HELP, "en", "")).toHaveLength(HELP.length);
    expect(searchHelp(HELP, "en", "zzz")).toHaveLength(0);
  });

  it("filters the questions on «Fragen» by every word, without accents and umlauts", () => {
    expect(matchesAll("Wo stelle ich die Kamera hin?", "kamera")).toBe(true);
    expect(matchesAll("Müssen die Spieler einverstanden sein?", "muessen spieler")).toBe(true);
    expect(matchesAll("Que devient la vidéo ?", "video")).toBe(true);
    expect(matchesAll("Was kostet es?", "kamera")).toBe(false);
    expect(matchesAll("Was kostet es?", "  ")).toBe(true);
  });
});

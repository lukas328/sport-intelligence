import { describe, expect, it } from "vitest";
import { HELP } from "../../content/help";
import { normalise, searchHelp } from "./search";

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
});

import { describe, expect, it } from "vitest";
import { currencyOf, guessCountry } from "./country";

describe("guessCountry: a club made by hand gets its country from the browser", () => {
  it("time zone first: a German-speaking browser in Zurich is a Swiss club", () => {
    expect(guessCountry(["de-DE"], "Europe/Zurich")).toBe("CH");
    expect(guessCountry(["de-CH"], "Europe/Berlin")).toBe("DE");
    expect(guessCountry(["fr"], "Europe/Paris")).toBe("FR");
    expect(guessCountry(["nb-NO"], "Europe/Oslo")).toBe("NO");
  });

  it("else the region of the browser's languages, else Switzerland", () => {
    expect(guessCountry(["da-DK", "en"], "UTC")).toBe("DK");
    expect(guessCountry(["en-US", "de-AT"], null)).toBe("AT");
    expect(guessCountry(["en"], "America/New_York")).toBe("CH");
    expect(guessCountry([], undefined)).toBe("CH");
  });
});

describe("currencyOf: the API's rule beside the choice", () => {
  it("CHF in Switzerland and Liechtenstein, else EUR", () => {
    expect(currencyOf("CH")).toBe("CHF");
    expect(currencyOf("LI")).toBe("CHF");
    expect(currencyOf("DE")).toBe("EUR");
    expect(currencyOf("SE")).toBe("EUR");
  });
});

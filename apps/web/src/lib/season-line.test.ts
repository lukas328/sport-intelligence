import { describe, expect, it } from "vitest";
import { lineRate, lineSevenM, lineShots } from "./season-line";

describe("season line figures", () => {
  it("makes the rate from the shots it shows (blocked ones excluded)", () => {
    const f = { goals: 17, shots: 20, seven_m_goals: 0, seven_m_shots: 0 };
    expect(lineShots(f)).toBe(20);
    expect(lineRate(f)).toBe("85 %");
    expect(lineRate({ goals: 17, shots: 21 })).toBe("81 %");
  });
  it("leaves never recorded figures empty", () => {
    expect(lineSevenM({ goals: 3, shots: 4, seven_m_goals: 0, seven_m_shots: 0 })).toBe("");
    expect(lineSevenM({ goals: 3, shots: 4, seven_m_goals: 2, seven_m_shots: 3 })).toBe("2/3");
    expect(lineRate({ goals: 0, shots: 0 })).toBe("");
  });
});

describe("website links", () => {
  it("always carry the language path (UX test N06)", async () => {
    const { sitePage } = await import("./site");
    expect(sitePage("https://handball-ai.ch", "de-CH", "aufnahme/")).toBe("https://handball-ai.ch/de/aufnahme/");
    expect(sitePage("https://handball-ai.ch/", "fr", "agb")).toBe("https://handball-ai.ch/fr/agb");
    expect(sitePage("https://example.org", "en")).toBe("https://example.org/en/");
  });
});

import { describe, expect, it } from "vitest";
import { cardFileName } from "./match-card";

describe("match card", () => {
  it("names the file after the match", () => {
    expect(cardFileName("Herren 1", "TV Müller-Thurgau", "01.11.26")).toBe("matchkarte-herren-1-tv-muller-thurgau-01-11-26.png");
  });
});

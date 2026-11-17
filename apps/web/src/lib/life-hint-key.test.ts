import { describe, expect, it } from "vitest";
import deCH from "../../messages/de-CH.json";
import { lifeHintKey } from "./life-hint-key";

const text = (key: string) => (deCH.teamLife as Record<string, string>)[key];

describe("lifeHintKey", () => {
  it("parents' overview names the dates only while Teamfunktionen are on", () => {
    expect(text(lifeHintKey("overview", "family", true))).toContain("Termine");
    expect(text(lifeHintKey("overview", "family", false))).not.toContain("Termine");
  });

  it("every area and reader has a text", () => {
    for (const area of ["dates", "plan", "assignments", "myscenes", "consents", "overview"] as const)
      for (const mode of ["staff", "player", "family"] as const)
        for (const on of [true, false]) expect(text(lifeHintKey(area, mode, on))).toBeTruthy();
  });
});

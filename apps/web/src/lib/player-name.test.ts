import { describe, expect, it } from "vitest";
import { playerLabel, reportName } from "./player-name";

describe("player names", () => {
  it("puts the first name first and drops the capitals of report names", () => {
    expect(reportName("ZUFALL Lisa")).toBe("Lisa Zufall");
    expect(reportName("MUSTERMANN Amy")).toBe("Amy Mustermann");
    expect(reportName("ÖRNEK Zerin")).toBe("Zerin Örnek");
    expect(reportName("Amy MUSTERMANN")).toBe("Amy Mustermann");
    expect(reportName("MÜLLER-MEIER Eva Maria")).toBe("Eva Maria Müller-Meier");
    expect(reportName("VON ARX Lea")).toBe("Lea von Arx");
    expect(reportName("D'AMICO  Sara ")).toBe("Sara D'Amico");
  });

  it("leaves names without capitals alone", () => {
    expect(reportName("Denise Sampler")).toBe("Denise Sampler");
    expect(reportName("Lea A. Muster")).toBe("Lea A. Muster");
    expect(reportName("ZUFALL")).toBe("Zufall");
    expect(reportName(null)).toBe("");
  });

  it("labels with the shirt number like the roster names", () => {
    expect(playerLabel(7, "Lisa Zufall")).toBe("#7 Lisa Zufall");
    expect(playerLabel(0, null)).toBe("#0");
    expect(playerLabel(null, "Lisa Zufall")).toBe("Lisa Zufall");
    expect(playerLabel(null, " ")).toBe("");
  });
});

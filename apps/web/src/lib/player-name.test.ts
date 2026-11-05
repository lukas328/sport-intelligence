import { describe, expect, it } from "vitest";
import { playerLabel, reportName } from "./player-name";

describe("player names", () => {
  it("puts the first name first and drops the capitals of report names", () => {
    expect(reportName("ZIMMERLI Lisa")).toBe("Lisa Zimmerli");
    expect(reportName("HOCHREUTENER Amy")).toBe("Amy Hochreutener");
    expect(reportName("ÖZCELIK Zerin")).toBe("Zerin Özcelik");
    expect(reportName("Amy HOCHREUTENER")).toBe("Amy Hochreutener");
    expect(reportName("MÜLLER-MEIER Eva Maria")).toBe("Eva Maria Müller-Meier");
    expect(reportName("VON ARX Lea")).toBe("Lea von Arx");
    expect(reportName("D'AMICO  Sara ")).toBe("Sara D'Amico");
  });

  it("leaves names without capitals alone", () => {
    expect(reportName("Denise Schwaiger")).toBe("Denise Schwaiger");
    expect(reportName("Lea A. Muster")).toBe("Lea A. Muster");
    expect(reportName("ZIMMERLI")).toBe("Zimmerli");
    expect(reportName(null)).toBe("");
  });

  it("labels with the shirt number like the roster names", () => {
    expect(playerLabel(7, "Lisa Zimmerli")).toBe("#7 Lisa Zimmerli");
    expect(playerLabel(0, null)).toBe("#0");
    expect(playerLabel(null, "Lisa Zimmerli")).toBe("Lisa Zimmerli");
    expect(playerLabel(null, " ")).toBe("");
  });
});

import { describe, expect, it } from "vitest";
import { colourChoicePath, shouldOfferColour } from "./colour-hint";

const base = { colorChosen: false, isAdmin: true, later: false, off: false, onChoicePage: false };

describe("«Vereinsfarbe wählen» (decision E8)", () => {
  it("shows for the admin of a club that never chose its colour", () => {
    expect(shouldOfferColour(base)).toBe(true);
  });

  it("not once the colour is chosen, not for coaches and players who cannot change it", () => {
    expect(shouldOfferColour({ ...base, colorChosen: true })).toBe(false);
    expect(shouldOfferColour({ ...base, isAdmin: false })).toBe(false);
  });

  it("waits after «Später» in the onboarding, stays away once closed, and not on the choice itself", () => {
    expect(shouldOfferColour({ ...base, later: true })).toBe(false);
    expect(shouldOfferColour({ ...base, off: true })).toBe(false);
    expect(shouldOfferColour({ ...base, onChoicePage: true })).toBe(false);
  });

  it("leads to the colour on the club page", () => {
    expect(colourChoicePath("o1")).toBe("/app/o1/club#vereinsfarbe");
  });
});

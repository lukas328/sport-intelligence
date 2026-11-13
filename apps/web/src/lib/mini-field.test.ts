import { describe, expect, it } from "vitest";
import { dotMetres, MINI } from "./mini-field";

// UX test round 2, N07: with the big field's dot size the players filled the small field.
describe("Minifeld", () => {
  it("draws a player well under a metre against the half court", () => {
    expect(dotMetres(MINI.width, MINI.dot)).toBeLessThan(1.2);
    // the old setting, 22 px on 56 px, was a dot of about eight metres
    expect(dotMetres(56, 22)).toBeGreaterThan(7);
  });
});

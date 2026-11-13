import { describe, expect, it } from "vitest";
import { CHECK_KITS, contrastRatio, COURT, GROUND, INK, kit, kitVars, near, OPPONENT_UNKNOWN, OPPONENT_UNKNOWN_ON_BLACK } from "./color";

describe("kit: the six check colours", () => {
  for (const [name, colours] of Object.entries(CHECK_KITS)) {
    it(`${name}: text on the club colour, the club colour as text and lines stay readable`, () => {
      const k = kit(colours);
      expect(contrastRatio(k.clubInk, k.club)).toBeGreaterThanOrEqual(4.5);
      expect(contrastRatio(k.clubText, GROUND)).toBeGreaterThanOrEqual(4.5);
      // a line that is too faint on the ground carries a piping that is not
      if (contrastRatio(k.clubLine, GROUND) < 2.4) {
        expect(k.clubPipe).not.toBeNull();
        expect(contrastRatio(k.clubPipe!, GROUND)).toBeGreaterThanOrEqual(3);
      } else {
        expect(k.clubPipe).toBeNull();
      }
      // on the dark court the club stays visible
      expect(contrastRatio(k.clubCam, COURT)).toBeGreaterThanOrEqual(2.2);
      expect(contrastRatio(k.clubCamInk, k.clubCam)).toBeGreaterThanOrEqual(3);
    });
  }

  it("white gets an ink edge and ink text, yellow is shifted, blue stays itself", () => {
    const white = kit(CHECK_KITS.weiss);
    expect(white.clubEdge).toBe(INK);
    expect(white.clubText).toBe(INK);
    expect(white.clubInk).toBe(INK);
    expect(white.clubPipe).toBe("#17191c");
    expect(kit(CHECK_KITS.gelb).clubText).not.toBe("#f6c500");
    expect(kit(CHECK_KITS.blau).clubText).toBe("#1f4fd6");
    expect(kit(CHECK_KITS.blau).clubInk).toBe("#ffffff");
  });

  it("black plays in its second colour on the camera", () => {
    expect(kit(CHECK_KITS.schwarz).clubCam).toBe("#ffffff");
  });
});

describe("kit: opponent", () => {
  it("never guesses an unknown colour", () => {
    for (const colours of Object.values(CHECK_KITS)) {
      const k = kit(colours, null);
      expect(k.oppKnown).toBe(false);
      expect(k.oppSource).toBe("unknown");
      // unknown opponents are grey rings on the camera
      expect(k.oppCam).toBe(COURT);
    }
    expect(kit(CHECK_KITS.blau, null).opp).toBe(OPPONENT_UNKNOWN);
    expect(kit(CHECK_KITS.schwarz, null).opp).toBe(OPPONENT_UNKNOWN_ON_BLACK);
    expect(kit(CHECK_KITS.blau, ["nope", "#ffffff"]).oppKnown).toBe(false);
  });

  it("keeps a distinct opponent colour", () => {
    const k = kit(CHECK_KITS.blau, ["#f6c500", "#17191c"]);
    expect(k).toMatchObject({ opp: "#f6c500", oppSource: "first", camClash: false, oppCam: "#f6c500" });
  });

  it("clash rule: second colour, then ink", () => {
    // navy against blue: hues within 45 degrees, the opponent plays white
    expect(kit(CHECK_KITS.blau, ["#1d3a8a", "#ffffff"])).toMatchObject({ opp: "#ffffff", oppSource: "second" });
    // both colours near ours: ink
    expect(kit(CHECK_KITS.blau, ["#1d3a8a", "#2a5ad0"])).toMatchObject({ opp: INK, oppSource: "ink" });
    // two blacks
    expect(kit(CHECK_KITS.schwarz, ["#17191c", "#ffffff"])).toMatchObject({ opp: "#ffffff", oppSource: "second" });
  });

  it("red against blue is no clash on the court: the hues differ, only the lightness is alike", () => {
    for (const [club, opp] of [
      [CHECK_KITS.blau, ["#d3202e", "#ffffff"]],
      [CHECK_KITS.rot, ["#1f4fd6", "#ffffff"]],
    ] as const) {
      const k = kit(club, opp);
      expect(k.camClash).toBe(false);
      expect(k.oppCam).toBe(opp[0]);
    }
  });

  it("steps back to grey rings only for the same colour family and a similar lightness", () => {
    // red against orange
    const ro = kit(CHECK_KITS.rot, ["#e2731c", "#e2731c"]);
    expect(ro.oppSource).toBe("ink");
    // the opponent is ink on the cloth; on the court ink falls back to orange: same family as red
    expect(ro.camClash).toBe(true);
    expect(ro.oppCam).toBe(COURT);
    expect(ro.oppCamEdge).toBe("#a3aeb8");
    // white against white: the opponent plays its second colour on the cloth, white again on the court
    const ww = kit(CHECK_KITS.weiss, ["#ffffff", "#17191c"]);
    expect(ww.opp).toBe("#17191c");
    expect(ww.camClash).toBe(true);
    // same family, clearly different lightness: no clash (blue against light blue)
    expect(kit(CHECK_KITS.blau, ["#7fb2ff", "#7fb2ff"]).camClash).toBe(false);
  });

  it("near(): hue and greys", () => {
    expect(near("#1f4fd6", "#1d3a8a")).toBe(true);
    expect(near("#1f4fd6", "#d3202e")).toBe(false);
    expect(near("#ffffff", "#eeeeee")).toBe(true);
    expect(near("#ffffff", "#17191c")).toBe(false);
  });
});

describe("kitVars", () => {
  it("sets every variable the components read", () => {
    const v = kitVars(kit(CHECK_KITS.weiss));
    expect(v["--club-pipe"]).toBe("#17191c");
    expect(v["--opp-pipe"]).toBe("transparent");
    expect(Object.keys(v)).toHaveLength(20);
  });
});

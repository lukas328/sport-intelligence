import { describe, expect, it } from "vitest";
import { clubTabs, hasClub, meTabs, settingsTarget } from "./settings-model";

describe("Ich and Verein", () => {
  it("splits the old settings page into two pages with one tab level", () => {
    expect(meTabs("o").map((t) => t.href)).toEqual(["/app/o/me", "/app/o/me/security", "/app/o/me/data"]);
    expect(clubTabs("o", { isAdmin: true, coachOf: 0, official: true }).map((t) => t.key)).toEqual(["club", "teams", "billing", "federation"]);
    expect(clubTabs("o", { isAdmin: true, coachOf: 0, official: false }).map((t) => t.key)).toEqual(["club", "teams", "billing"]);
    // a coach sees teams and roles only; a player no club page at all
    expect(clubTabs("o", { isAdmin: false, coachOf: 1, official: true }).map((t) => t.key)).toEqual(["teams"]);
    expect(hasClub({ isAdmin: false, coachOf: 0, official: false })).toBe(false);
    expect(clubTabs("o", { isAdmin: false, coachOf: 0, official: false })).toEqual([]);
  });

  it("sends old settings anchors to their new place", () => {
    expect(settingsTarget("o", true)).toBe("/app/o/club");
    expect(settingsTarget("o", false)).toBe("/app/o/me");
    expect(settingsTarget("o", true, "security")).toBe("/app/o/me/security");
    expect(settingsTarget("o", true, "billing")).toBe("/app/o/club/billing");
    expect(settingsTarget("o", true, "official-section")).toBe("/app/o/club/federation");
    expect(settingsTarget("o", false, "privacy")).toBe("/app/o/me/data");
  });
});

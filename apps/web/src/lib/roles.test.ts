import { describe, expect, it } from "vitest";
import { canDelete, canGive, coachRights, personRole, storedRoles, worksWithVideo } from "./roles";

describe("the four roles (K18)", () => {
  it("maps the stored roles onto Trainer, Co-Trainer, Spieler and Eltern", () => {
    expect(personRole("org_admin", "coach")).toBe("trainer");
    expect(personRole("member", "coach")).toBe("co_trainer");
    for (const r of ["analyst", "team_manager", "goalkeeper_coach", "athletic_coach"]) {
      expect(personRole("member", r)).toBe("co_trainer");
      expect(personRole("org_admin", r)).toBe("trainer");
    }
    expect(personRole("member", "goalkeeper")).toBe("player");
    expect(personRole("member", "player")).toBe("player");
    expect(personRole("member", "parent")).toBe("parent");
    expect(personRole("member", "guest")).toBeNull();
    expect(personRole("org_admin", null)).toBe("trainer");
  });

  it("stores a Trainer as coach and club admin", () => {
    expect(storedRoles("trainer")).toEqual({ org_role: "org_admin", team_role: "coach" });
    expect(storedRoles("co_trainer")).toEqual({ org_role: "member", team_role: "coach" });
    expect(storedRoles("player")).toEqual({ org_role: "member", team_role: "player" });
    expect(storedRoles("parent")).toEqual({ org_role: "member", team_role: "parent" });
  });

  it("lets players work with the video but not delete", () => {
    expect(worksWithVideo("member", "player")).toBe(true);
    expect(canDelete("member", "player")).toBe(false);
    expect(coachRights("member", "player")).toBe(false);
    expect(canDelete("member", "analyst")).toBe(true);
    expect(worksWithVideo("member", "parent")).toBe(false);
    expect(canGive("member", "trainer")).toBe(false);
    expect(canGive("org_admin", "trainer")).toBe(true);
    expect(canGive("member", "co_trainer")).toBe(true);
  });
});

/**
 * The product's four roles (finding K18, decided 2026-11-16): Trainer, Co-Trainer, Spieler,
 * Eltern. The stored roles stay (organisation role and team role, `models/enums.py`) and map onto
 * them, like `services/policies.py` `person_role` on the server:
 *
 * - Trainer: coach of the team and club admin; everything.
 * - Co-Trainer: coach rights in the team, without club and subscription. Stored as `coach`, or as
 *   one of the older specialist roles (analyst, team manager, goalkeeper and athletic coach).
 * - Spieler: `player` and `goalkeeper` (a player with a position). See everything of the team,
 *   mark scenes, build collections and share them by link, comment, upload videos. No deleting,
 *   no inviting, no squad, team, club or subscription.
 * - Eltern: `parent`, only their own children.
 *
 * Guests have no role in the team: they see shared links only.
 */

export type PersonRole = "trainer" | "co_trainer" | "player" | "parent";

/** The roles one can invite or give, in the order they are offered. */
export const PERSON_ROLES: readonly PersonRole[] = ["co_trainer", "player", "parent", "trainer"];

const COACH_ROLES = new Set(["coach", "analyst", "team_manager", "goalkeeper_coach", "athletic_coach"]);
const PLAYER_ROLES = new Set(["player", "goalkeeper"]);

export function personRole(orgRole: string | null | undefined, teamRole: string | null | undefined): PersonRole | null {
  if (COACH_ROLES.has(teamRole ?? "")) return orgRole === "org_admin" ? "trainer" : "co_trainer";
  if (PLAYER_ROLES.has(teamRole ?? "")) return "player";
  if (teamRole === "parent") return "parent";
  if (orgRole === "org_admin") return "trainer";
  return null;
}

/** What is stored for a new member with a role (invitations). */
export function storedRoles(role: PersonRole): { org_role: "org_admin" | "member"; team_role: "coach" | "player" | "parent" } {
  if (role === "trainer") return { org_role: "org_admin", team_role: "coach" };
  if (role === "co_trainer") return { org_role: "member", team_role: "coach" };
  if (role === "player") return { org_role: "member", team_role: "player" };
  return { org_role: "member", team_role: "parent" };
}

/** Trainer or Co-Trainer: coach rights in the team (squad, invitations, deleting, Teamleben). */
export function coachRights(orgRole: string | null | undefined, teamRole: string | null | undefined): boolean {
  return orgRole === "org_admin" || COACH_ROLES.has(teamRole ?? "");
}

/** Trainer, Co-Trainer and players work with the video: upload, scenes, collections, sharing. */
export function worksWithVideo(orgRole: string | null | undefined, teamRole: string | null | undefined): boolean {
  return coachRights(orgRole, teamRole) || PLAYER_ROLES.has(teamRole ?? "");
}

/** Deleting matches and videos: the staff only. */
export function canDelete(orgRole: string | null | undefined, teamRole: string | null | undefined): boolean {
  return coachRights(orgRole, teamRole);
}

/** Who may give a role: Trainer only to and from a Trainer, Co-Trainer the others. */
export function canGive(myOrgRole: string | null | undefined, role: PersonRole): boolean {
  return role === "trainer" ? myOrgRole === "org_admin" : true;
}

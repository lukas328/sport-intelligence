/**
 * "Ich" and "Verein" (SPEC section 6) replace the single settings page: two pages, one level of
 * tabs each. Which tabs a person sees follows the policy table: the club, its billing and the
 * federation link are for admins; teams, roles and "Teamfunktionen" for admins and coaches.
 */
export type MeTab = "profile" | "security" | "data";
export type ClubTab = "club" | "teams" | "billing" | "federation";

export interface Tab<K extends string> {
  key: K;
  href: string;
}

export function meTabs(orgId: string): Tab<MeTab>[] {
  const base = `/app/${orgId}/me`;
  return [
    { key: "profile", href: base },
    { key: "security", href: `${base}/security` },
    { key: "data", href: `${base}/data` },
  ];
}

export interface ClubAccess {
  isAdmin: boolean;
  /** coach of at least one team (may invite and change team settings) */
  coachOf: number;
  /** the club was taken over from the official data */
  official: boolean;
}

export function clubTabs(orgId: string, a: ClubAccess): Tab<ClubTab>[] {
  const base = `/app/${orgId}/club`;
  const tabs: (Tab<ClubTab> | null)[] = [
    a.isAdmin ? { key: "club", href: base } : null,
    a.isAdmin || a.coachOf > 0 ? { key: "teams", href: `${base}/teams` } : null,
    a.isAdmin ? { key: "billing", href: `${base}/billing` } : null,
    a.isAdmin && a.official ? { key: "federation", href: `${base}/federation` } : null,
  ];
  return tabs.filter((x): x is Tab<ClubTab> => x !== null);
}

/** Whether "Verein" appears in the account menu at all. */
export function hasClub(a: ClubAccess): boolean {
  return a.isAdmin || a.coachOf > 0;
}

/** Old settings anchors and pages, mapped to their new place. */
export function settingsTarget(orgId: string, isAdmin: boolean, anchor?: string | null): string {
  const me = `/app/${orgId}/me`;
  const club = `/app/${orgId}/club`;
  switch (anchor) {
    case "security":
      return `${me}/security`;
    case "privacy":
      return `${me}/data`;
    case "account-section":
      return me;
    case "billing":
      return `${club}/billing`;
    case "official-section":
      return `${club}/federation`;
    case "people-section":
    case "team-features":
      return `${club}/teams`;
    default:
      return isAdmin ? club : me;
  }
}

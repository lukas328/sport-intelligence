/**
 * Plan features of the club (`OrgOut.features`, packages/plans). A club whose answer carries no
 * list (an older API) keeps every feature: the API itself refuses what the plan lacks.
 */
export function hasFeature(features: readonly string[] | null | undefined, feature: string): boolean {
  return features == null || features.includes(feature);
}

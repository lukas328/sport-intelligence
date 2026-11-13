/**
 * The figures of a season line (UX test N12): shots are the attempts without blocked ones (BRIEF
 * 4.8), the same count the rate is made from, so «17 of 20» and «85 %» always agree. A 7 m count
 * without a single attempt is empty, not «0/0».
 */
export interface LineCounts {
  goals: number;
  shots: number;
  seven_m_goals: number;
  seven_m_shots: number;
}

export const lineShots = (f: LineCounts): number => f.shots;

export function lineRate(f: Pick<LineCounts, "goals" | "shots">): string {
  return f.shots > 0 ? `${Math.round((f.goals / f.shots) * 100)} %` : "";
}

export const lineSevenM = (f: LineCounts): string => (f.seven_m_shots > 0 ? `${f.seven_m_goals}/${f.seven_m_shots}` : "");

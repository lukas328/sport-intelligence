"use client";

import { useQueryClient } from "@tanstack/react-query";
import { TrainingTips } from "@/components/training/training-tips";
import { refreshList } from "@/lib/refresh-list";

/** The tips under Saison: the planned unit lands in the training plan, linked from here. */
export function SeasonTips({ orgId, teamId, tasks }: { orgId: string; teamId: string; tasks: boolean }) {
  const qc = useQueryClient();
  return (
    <TrainingTips
      orgId={orgId}
      teamId={teamId}
      heading={false}
      tasks={tasks}
      planHref={`/app/${orgId}/teams/${teamId}/training`}
      onPlanned={() => void refreshList(qc, ["sessions", teamId])}
    />
  );
}

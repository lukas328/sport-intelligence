import { Suspense } from "react";
import { NewPlay } from "./new-play";

export default async function NewPlayPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return (
    <Suspense>
      <NewPlay orgId={orgId} teamId={teamId} />
    </Suspense>
  );
}

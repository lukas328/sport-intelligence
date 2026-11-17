import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { NewPlay } from "./new-play";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("tactics"))("new") };
}

export default async function NewPlayPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return (
    <Suspense>
      <NewPlay orgId={orgId} teamId={teamId} />
    </Suspense>
  );
}

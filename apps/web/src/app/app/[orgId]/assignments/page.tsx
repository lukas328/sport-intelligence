import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { MyAssignments } from "./my-assignments";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("assignments"))("mine") };
}

export default async function AssignmentsPage({ params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  return <MyAssignments orgId={orgId} />;
}

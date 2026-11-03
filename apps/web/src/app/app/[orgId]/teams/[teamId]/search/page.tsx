import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { SearchView } from "./search-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("search"))("title") };
}

export default async function SearchPage({ params }: { params: Promise<{ orgId: string; teamId: string }> }) {
  const { orgId, teamId } = await params;
  return <SearchView orgId={orgId} teamId={teamId} />;
}

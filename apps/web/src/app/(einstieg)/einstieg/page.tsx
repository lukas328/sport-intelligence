import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { EntryView } from "./entry-view";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("entry"))("ask") };
}

/** The public entry: no account needed (UX test, second delivery). */
export default function EntryPage() {
  return (
    <Suspense>
      <EntryView />
    </Suspense>
  );
}

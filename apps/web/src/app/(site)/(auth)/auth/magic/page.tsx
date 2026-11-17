import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { ConsumeMagicLink } from "./consume";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getTranslations("auth"))("magicTitle") };
}

export default function MagicPage() {
  return (
    <Suspense>
      <ConsumeMagicLink />
    </Suspense>
  );
}

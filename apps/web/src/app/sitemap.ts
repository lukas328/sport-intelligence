import type { MetadataRoute } from "next";
import { appOrigin } from "@/lib/app-origin";

/** Only the public entry of the app (finding L11); the product is described on the website. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const origin = await appOrigin();
  return [{ url: `${origin}/einstieg`, changeFrequency: "monthly", priority: 1 }];
}

import { PageSkeleton } from "@/components/ui/page-skeleton";

/** Spiele, Szenen, Saison and Team open with the shape of the page; the team layout above has already answered «not found» for an unknown team (review R40). */
export default function Loading() {
  return <PageSkeleton kind="page" />;
}

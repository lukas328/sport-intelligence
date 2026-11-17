import { PageSkeleton } from "@/components/ui/page-skeleton";

/** A match opens with the shape of its head at once; the layout above has already answered «not found» for an unknown match (review R40). */
export default function Loading() {
  return <PageSkeleton kind="match" />;
}

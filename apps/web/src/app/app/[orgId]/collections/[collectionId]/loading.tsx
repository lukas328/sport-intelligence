import { PageSkeleton } from "@/components/ui/page-skeleton";

/** A collection opens with the shape of the page; the layout above has already answered «not found» (review R40). */
export default function Loading() {
  return <PageSkeleton kind="page" />;
}

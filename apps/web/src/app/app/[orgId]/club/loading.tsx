import { PageSkeleton } from "@/components/ui/page-skeleton";

/** Verein opens with the shape of a form; the club layout above checks the access (review R40). */
export default function Loading() {
  return <PageSkeleton kind="form" />;
}

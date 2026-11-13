import { Skeleton } from "@/components/ui/card";

/*
 * The skeleton of the club start only. A skeleton for the whole club area would start the
 * stream before a page could answer «not found», so unknown match, team and collection
 * addresses answered 200 (UX test N18).
 */
export default function Loading() {
  return (
    <div className="space-y-8" aria-busy="true">
      <div className="space-y-3">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-9 w-72 max-w-full" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Skeleton className="h-64" />
        <Skeleton className="h-40" />
      </div>
      <Skeleton className="h-48" />
    </div>
  );
}

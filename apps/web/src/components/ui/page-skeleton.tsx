import { useTranslations } from "next-intl";
import { Skeleton } from "@/components/ui/card";

/**
 * What a page change shows while the server still answers (review R40: two to four seconds of
 * nothing): the shape of the page that comes, and «Wird geladen …» for screen readers. One shape
 * per kind of page: a match with its head, a page with a title and rows, a form page.
 */
export function PageSkeleton({ kind = "page" }: { kind?: "match" | "page" | "form" }) {
  const t = useTranslations("common");
  return (
    <div className="space-y-8" aria-busy="true" data-testid="page-skeleton">
      <p role="status" className="sr-only">
        {t("loading")}
      </p>
      {kind === "match" ? (
        <>
          {/* the result head: the club area with title and score */}
          <div className="bleed-x -mt-6 lg:-mt-8">
            <Skeleton className="h-[300px] md:h-[410px]" />
          </div>
          <div className="flex gap-6">
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-20" />
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            <Skeleton className="h-56" />
            <Skeleton className="h-56 max-md:hidden" />
            <Skeleton className="h-56 max-md:hidden" />
          </div>
        </>
      ) : (
        <>
          <div className="space-y-3">
            <Skeleton className="h-3 w-40" />
            <Skeleton className="h-10 w-80 max-w-full" />
          </div>
          {kind === "form" ? (
            <div className="max-w-3xl space-y-4">
              <Skeleton className="h-8 w-72 max-w-full" />
              <Skeleton className="h-11" />
              <Skeleton className="h-11" />
              <Skeleton className="h-32" />
            </div>
          ) : (
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
              <div className="space-y-3">
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
              </div>
              <Skeleton className="h-48 max-lg:hidden" />
            </div>
          )}
        </>
      )}
    </div>
  );
}

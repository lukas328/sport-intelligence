import { forwardRef } from "react";
import type { ComponentProps, ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";

/** A white panel on the paper background. No heavy borders: a hairline and space do the work. */
export function Card({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("rounded-lg border border-border bg-raised p-5 sm:p-6", className)} {...props} />;
}

/** An open section of a match sheet: a strong rule on top instead of a panel around it. */
export const Sheet = forwardRef<HTMLElement, ComponentProps<"section">>(function Sheet({ className, ...props }, ref) {
  return <section ref={ref} className={cn("border-t-2 border-foreground pt-4", className)} {...props} />;
});

export function CardTitle({ children, as: Tag = "h2", className }: { children: ReactNode; as?: "h1" | "h2" | "h3"; className?: string }) {
  return <Tag className={cn("text-lg font-bold font-display", className)}>{children}</Tag>;
}

export function Alert({
  kind = "error",
  children,
  className,
}: {
  kind?: "error" | "info" | "success";
  children: ReactNode;
  className?: string;
}) {
  const Icon = { error: AlertCircle, info: Info, success: CheckCircle2 }[kind];
  const tone = { error: "text-error", info: "text-accent", success: "text-ok" }[kind];
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-md bg-surface px-4 py-3 text-sm", className)}
    >
      <Icon aria-hidden className={cn("mt-0.5 size-4 shrink-0", tone)} />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

/** What is missing and what to do next, never just "no data". */
export function EmptyState({
  title,
  children,
  icon,
  action,
  className,
}: {
  title: string;
  children?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-start rounded-lg border border-dashed border-foreground/20 px-6 py-10", className)}>
      {icon && <div className="mb-4 text-muted [&_svg]:size-6">{icon}</div>}
      <p className="text-lg font-bold font-display">{title}</p>
      {children && <div className="mt-1 max-w-lg text-[0.9375rem] text-muted">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/** A titled block of a page. */
export function Section({
  title,
  description,
  actions,
  children,
  className,
  id,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section id={id} className={cn("space-y-4", className)}>
      {(title || actions) && (
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            {title && <h2 className="text-2xl">{title}</h2>}
            {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-md bg-surface", className)} />;
}

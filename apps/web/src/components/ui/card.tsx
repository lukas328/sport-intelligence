import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-border bg-background p-5 shadow-sm", className)} {...props} />;
}

export function CardTitle({ children, as: Tag = "h2" }: { children: ReactNode; as?: "h1" | "h2" | "h3" }) {
  return <Tag className="text-lg font-semibold">{children}</Tag>;
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
  const styles = {
    error: "border-error text-error",
    info: "border-accent text-foreground",
    success: "border-ok text-ok",
  }[kind];
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      className={cn("rounded-md border-l-4 bg-surface px-4 py-3 text-sm", styles, className)}
    >
      {children}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-border p-8 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-2 text-sm text-muted">{children}</div>}
    </div>
  );
}

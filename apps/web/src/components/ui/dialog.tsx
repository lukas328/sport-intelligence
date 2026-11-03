"use client";

import * as D from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export const DialogRoot = D.Root;
export const DialogTrigger = D.Trigger;
export const DialogClose = D.Close;

/** Centered dialog on desktop, bottom sheet on phones. */
export function DialogContent({
  title,
  description,
  children,
  className,
  wide,
}: {
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  className?: string;
  wide?: boolean;
}) {
  const t = useTranslations("common");
  return (
    <D.Portal>
      <D.Overlay className="fixed inset-0 z-50 bg-[var(--overlay)] animate-fade" />
      <D.Content
        aria-describedby={description ? undefined : undefined}
        className={cn(
          "club fixed z-50 flex max-h-[92dvh] w-full flex-col overflow-hidden bg-raised shadow-2xl ring-1 ring-border animate-rise",
          "inset-x-0 bottom-0 rounded-t-3xl sm:inset-auto sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-3xl",
          wide ? "sm:max-w-3xl" : "sm:max-w-lg",
          className,
        )}
      >
        <div className="flex items-start justify-between gap-4 px-6 pt-6">
          <div className="min-w-0">
            <D.Title className="text-lg font-semibold">{title}</D.Title>
            {description ? (
              <D.Description className="mt-1 text-sm text-muted">{description}</D.Description>
            ) : (
              <D.Description className="sr-only">{title}</D.Description>
            )}
          </div>
          <D.Close
            aria-label={t("close")}
            className="-mr-2 -mt-1 grid size-9 shrink-0 place-items-center rounded-full text-muted hover:bg-surface hover:text-foreground"
          >
            <X aria-hidden className="size-4" />
          </D.Close>
        </div>
        <div className="overflow-y-auto px-6 pt-4 pb-6">{children}</div>
      </D.Content>
    </D.Portal>
  );
}

export function Dialog({
  open,
  onOpenChange,
  trigger,
  ...content
}: {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  trigger?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  className?: string;
  wide?: boolean;
}) {
  return (
    <D.Root {...(open !== undefined ? { open } : {})} {...(onOpenChange ? { onOpenChange } : {})}>
      {trigger && <D.Trigger asChild>{trigger}</D.Trigger>}
      <DialogContent {...content} />
    </D.Root>
  );
}

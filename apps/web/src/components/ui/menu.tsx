"use client";

import * as M from "@radix-ui/react-dropdown-menu";
import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export const MenuRoot = M.Root;
export const MenuTrigger = M.Trigger;

export function MenuContent({ children, align = "end", className, side }: { children: ReactNode; align?: "start" | "end" | "center"; className?: string; side?: "top" | "bottom" | "right" | "left" }) {
  return (
    <M.Portal>
      <M.Content
        align={align}
        side={side}
        sideOffset={6}
        collisionPadding={12}
        className={cn(
          "club z-50 min-w-56 overflow-hidden bg-raised p-1.5 text-sm ring-1 ring-border animate-fade",
          className,
        )}
      >
        {children}
      </M.Content>
    </M.Portal>
  );
}

const item =
  "flex w-full cursor-pointer select-none items-center gap-3 px-3 py-2 text-left outline-none" +
  "data-[highlighted]:bg-surface data-[disabled]:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:text-muted";

export function MenuItem({
  children,
  onSelect,
  href,
  icon,
  danger,
  disabled,
  external,
  testId,
}: {
  children: ReactNode;
  onSelect?: () => void;
  href?: string;
  icon?: ReactNode;
  danger?: boolean;
  disabled?: boolean;
  /** plain <a> (downloads, API routes) instead of client navigation */
  external?: boolean;
  testId?: string;
}) {
  const cls = cn(item, danger && "text-error [&_svg]:text-error");
  const body = (
    <>
      {icon}
      <span className="flex-1">{children}</span>
    </>
  );
  if (href) {
    return (
      <M.Item asChild disabled={disabled}>
        {external ? (
          <a href={href} className={cls} data-testid={testId}>
            {body}
          </a>
        ) : (
          <Link href={href} className={cls} data-testid={testId}>
            {body}
          </Link>
        )}
      </M.Item>
    );
  }
  return (
    <M.Item className={cls} onSelect={onSelect} disabled={disabled} data-testid={testId}>
      {body}
    </M.Item>
  );
}

export function MenuLabel({ children }: { children: ReactNode }) {
  return <M.Label className="px-3 pt-2 pb-1 eyebrow">{children}</M.Label>;
}

export function MenuSeparator() {
  return <M.Separator className="my-1.5 h-px bg-border" />;
}

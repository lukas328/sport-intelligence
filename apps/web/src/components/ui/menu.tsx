"use client";

import * as M from "@radix-ui/react-dropdown-menu";
import { ExternalLink } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export const MenuRoot = M.Root;
export const MenuTrigger = M.Trigger;

/**
 * The panel of every drop-down menu (finding A1): a 2 px ink frame with the hard offset shadow of
 * the app's sheets, no soft ring. The bell's panel uses the same surface.
 */
export const MENU_SURFACE =
  "club z-50 overflow-hidden border-2 border-ink bg-paper text-[15px] text-ink shadow-[4px_4px_0_var(--ink)] animate-fade";

/** One entry as the app writes a choice: semi-bold, ink icons, inverted (ink, light text) while it
 * is the chosen one, by mouse or keyboard. */
export const MENU_ITEM =
  "flex min-h-11 w-full cursor-pointer select-none items-center gap-3 px-3 py-2 text-left font-semibold text-ink no-underline outline-none " +
  "data-[highlighted]:bg-ink data-[highlighted]:text-ground data-[disabled]:cursor-default data-[disabled]:opacity-50 " +
  "[&_svg]:size-[18px] [&_svg]:shrink-0 [&_svg]:text-ink data-[highlighted]:[&_svg]:text-ground";

export function MenuContent({ children, align = "end", className, side }: { children: ReactNode; align?: "start" | "end" | "center"; className?: string; side?: "top" | "bottom" | "right" | "left" }) {
  return (
    <M.Portal>
      <M.Content
        align={align}
        side={side}
        sideOffset={6}
        collisionPadding={12}
        // never cut off on a small screen: as high as there is room, the rest scrolls (UX-11)
        className={cn(MENU_SURFACE, "max-h-[var(--radix-dropdown-menu-content-available-height)] min-w-56 overflow-y-auto overscroll-contain p-1.5", className)}
      >
        {children}
      </M.Content>
    </M.Portal>
  );
}

// a destructive entry: red, with room above it (callers put a separator before it)
const DANGER =
  "mt-1 text-loss [&_svg]:text-loss data-[highlighted]:bg-loss data-[highlighted]:text-white data-[highlighted]:[&_svg]:text-white";

export function MenuItem({
  children,
  onSelect,
  href,
  icon,
  danger,
  disabled,
  external,
  newTab,
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
  /** opens in a new tab and says so (help pages outside the app, review R19); the words for
   * screen readers come with it */
  newTab?: string;
  testId?: string;
}) {
  const cls = cn(MENU_ITEM, danger && DANGER);
  const body = (
    <>
      {icon}
      <span className="flex-1">{children}</span>
    </>
  );
  if (href && newTab) {
    return (
      <M.Item asChild disabled={disabled}>
        <a href={href} target="_blank" rel="noopener noreferrer" className={cls} data-testid={testId}>
          {icon}
          <span className="flex-1">
            {children}
            <span className="sr-only"> ({newTab})</span>
          </span>
          <ExternalLink aria-hidden className="!size-3.5" />
        </a>
      </M.Item>
    );
  }
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
  // full width and firm, like the rule over a section of the match sheet
  return <M.Separator className="-mx-1.5 my-1.5 h-0.5 bg-ink/80" />;
}

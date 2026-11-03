"use client";

import * as D from "@radix-ui/react-dialog";
import { useTranslations } from "next-intl";
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { Button } from "./button";

interface Ask {
  title: string;
  body?: string;
  confirm?: string;
  danger?: boolean;
}

const Ctx = createContext<(ask: Ask) => Promise<boolean>>(async () => false);

/** `const confirm = useConfirm(); if (await confirm({ title })) ...` instead of window.confirm. */
export function useConfirm() {
  return useContext(Ctx);
}

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const t = useTranslations("common");
  const [ask, setAsk] = useState<Ask | null>(null);
  const resolver = useRef<((ok: boolean) => void) | null>(null);
  const open = useCallback(
    (a: Ask) =>
      new Promise<boolean>((resolve) => {
        resolver.current = resolve;
        setAsk(a);
      }),
    [],
  );
  function close(ok: boolean) {
    resolver.current?.(ok);
    resolver.current = null;
    setAsk(null);
  }
  return (
    <Ctx.Provider value={open}>
      {children}
      <D.Root open={ask !== null} onOpenChange={(o) => !o && close(false)}>
        <D.Portal>
          <D.Overlay className="fixed inset-0 z-[60] bg-[var(--overlay)] animate-fade" />
          <D.Content
            role="alertdialog"
            className="club fixed inset-x-4 top-1/2 z-[60] mx-auto max-w-sm -translate-y-1/2 rounded-3xl bg-raised p-6 shadow-2xl ring-1 ring-border animate-rise"
          >
            <D.Title className="text-lg font-semibold">{ask?.title}</D.Title>
            <D.Description className={ask?.body ? "mt-2 text-sm text-muted" : "sr-only"}>{ask?.body ?? ask?.title}</D.Description>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => close(false)}>
                {t("cancel")}
              </Button>
              <Button variant={ask?.danger ? "danger" : "primary"} onClick={() => close(true)} data-testid="confirm-ok">
                {ask?.confirm ?? t("confirm")}
              </Button>
            </div>
          </D.Content>
        </D.Portal>
      </D.Root>
    </Ctx.Provider>
  );
}

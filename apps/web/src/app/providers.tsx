"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { ConfirmProvider } from "@/components/ui/confirm";
import { FormMessages } from "@/components/ui/form-messages";
import { rememberSource } from "@/lib/signup-source";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } }),
  );
  // the website's `?src=<place>`, kept for the sign-up in this tab (no cookie)
  useEffect(() => rememberSource(window.location.search), []);
  return (
    <QueryClientProvider client={client}>
      <ConfirmProvider>
        <FormMessages />
        {children}
      </ConfirmProvider>
    </QueryClientProvider>
  );
}

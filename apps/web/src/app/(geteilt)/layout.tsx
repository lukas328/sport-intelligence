import type { ReactNode } from "react";

/** A shared link (SPEC 7.8): no site bar, the page brings the club's own narrow head. */
export default function SharedLayout({ children }: { children: ReactNode }) {
  return (
    <main id="main" className="mx-auto min-h-dvh w-full max-w-6xl px-4 pb-16 sm:px-6">
      {children}
    </main>
  );
}

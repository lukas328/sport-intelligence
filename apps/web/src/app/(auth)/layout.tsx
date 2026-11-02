import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-md py-6">{children}</div>;
}

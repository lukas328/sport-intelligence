import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-[26rem] pt-2 sm:pt-8">{children}</div>;
}

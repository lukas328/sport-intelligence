"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { buttonClass } from "@/components/ui/button";

/** «Anmelden» in the public head, but not on the sign-in page itself: one «Anmelden» per screen
 * (UX test B46). */
export function SiteLoginLink({ signedIn, label }: { signedIn: boolean; label: string }) {
  const path = usePathname();
  if (!signedIn && path === "/login") return null;
  return (
    <Link href={signedIn ? "/app" : "/login"} className={buttonClass("secondary", "sm")}>
      {label}
    </Link>
  );
}

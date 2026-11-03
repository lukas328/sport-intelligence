import { NextResponse, type NextRequest } from "next/server";

const PROTECTED = ["/app", "/onboarding", "/ops"];

/**
 * Content Security Policy, built at runtime so the storage origin for direct uploads can be
 * configured per deployment (HB_S3_PUBLIC_URL). Scripts: 'unsafe-inline' is still needed for
 * Next.js inline bootstrap; nonces follow in M9 (OPEN_QUESTIONS).
 */
export function csp(storageOrigin: string | undefined, dev: boolean): string {
  const connect = ["'self'", storageOrigin].filter(Boolean).join(" ");
  return [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "media-src 'self' blob:",
    `connect-src ${connect}`,
    "worker-src 'self' blob:",
    "font-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self' https://accounts.google.com https://appleid.apple.com",
  ].join("; ");
}

function originOf(url: string | undefined): string | undefined {
  try {
    return url ? new URL(url).origin : undefined;
  } catch {
    return undefined;
  }
}

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`)) && !req.cookies.get("hb_session")) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  const res = NextResponse.next();
  res.headers.set("Content-Security-Policy", csp(originOf(process.env.HB_S3_PUBLIC_URL), process.env.NODE_ENV !== "production"));
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|v1/).*)"],
};

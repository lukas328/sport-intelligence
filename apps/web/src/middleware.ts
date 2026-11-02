import { NextResponse, type NextRequest } from "next/server";

const PROTECTED = ["/app", "/onboarding"];

/** Cheap guard: no session cookie means sign in first. The API validates the session itself. */
export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`)) && !req.cookies.get("hb_session")) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/app/:path*", "/onboarding/:path*", "/app", "/onboarding"] };

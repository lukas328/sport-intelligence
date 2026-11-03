import { LOCALE_COOKIE, locales } from "@/i18n/config";
import { NextResponse, type NextRequest } from "next/server";

const PROTECTED = ["/app", "/onboarding", "/ops"];

/**
 * Content Security Policy, built at runtime so the storage origin for direct uploads can be
 * configured per deployment (HB_S3_PUBLIC_URL). Scripts: 'unsafe-inline' is still needed for
 * Next.js inline bootstrap; nonces follow in M9 (OPEN_QUESTIONS).
 */
export interface ThirdParties {
  analyticsHost?: string | undefined; // PostHog, only when configured (loaded after consent)
  crisp?: boolean; // support chat, loaded only on click
}

export function thirdPartiesFromEnv(env: Record<string, string | undefined>): ThirdParties {
  return {
    analyticsHost: env.NEXT_PUBLIC_POSTHOG_KEY ? (env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://eu.i.posthog.com") : undefined,
    crisp: env.HB_CRISP_ENABLED === "1",
  };
}

export function csp(storageOrigin: string | undefined, dev: boolean, third: ThirdParties = {}): string {
  const analytics = originOf(third.analyticsHost);
  const assets = analytics ? analytics.replace("://", "://eu-assets.").replace("eu-assets.eu.", "eu-assets.") : undefined;
  const crispScript = third.crisp ? ["https://client.crisp.chat"] : [];
  const crispConnect = third.crisp ? ["https://client.crisp.chat", "wss://client.relay.crisp.chat"] : [];
  const connect = ["'self'", storageOrigin, analytics, ...crispConnect].filter(Boolean).join(" ");
  const scripts = ["'self'", "'unsafe-inline'", ...(dev ? ["'unsafe-eval'"] : []), ...(assets ? [assets] : []), ...crispScript];
  return [
    "default-src 'self'",
    `script-src ${scripts.join(" ")}`,
    `style-src 'self' 'unsafe-inline'${third.crisp ? " https://client.crisp.chat" : ""}`,
    `img-src 'self' data: blob:${third.crisp ? " https://image.crisp.chat https://client.crisp.chat" : ""}`,
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
  // links from the marketing site carry ?lang=de-CH|fr|en: remember it and drop the parameter
  const lang = req.nextUrl.searchParams.get("lang");
  if (lang && (locales as readonly string[]).includes(lang)) {
    const url = req.nextUrl.clone();
    url.searchParams.delete("lang");
    const redirect = NextResponse.redirect(url);
    redirect.cookies.set(LOCALE_COOKIE, lang, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
    return redirect;
  }
  const res = NextResponse.next();
  res.headers.set(
    "Content-Security-Policy",
    csp(originOf(process.env.HB_S3_PUBLIC_URL), process.env.NODE_ENV !== "production", thirdPartiesFromEnv(process.env)),
  );
  // HSTS only when the request really came in over HTTPS (never on local http)
  const proto = req.headers.get("x-forwarded-proto") ?? req.nextUrl.protocol.replace(":", "");
  if (proto === "https") res.headers.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains");
  res.headers.set("X-Frame-Options", "DENY");
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|v1/).*)"],
};

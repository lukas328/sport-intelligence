import type { NextRequest } from "next/server";
import { apiBaseUrl } from "@/lib/api-base";

/**
 * Same-origin proxy to the API. The browser only talks to the web origin, so session cookies
 * stay first-party (httpOnly, SameSite=Lax) and the CSP can keep connect-src 'self'.
 */
export const dynamic = "force-dynamic";

const FORWARD_REQUEST = ["cookie", "content-type", "x-csrf-token", "x-request-id", "origin", "user-agent", "accept"];
const DROP_RESPONSE = new Set(["content-encoding", "content-length", "transfer-encoding", "connection"]);

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }): Promise<Response> {
  const { path } = await ctx.params;
  const target = `${apiBaseUrl()}/v1/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;
  const headers = new Headers();
  for (const name of FORWARD_REQUEST) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) headers.set("x-forwarded-for", forwarded);
  const hasBody = !["GET", "HEAD"].includes(req.method);
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { title: "Bad Gateway", status: 502, detail: "API unreachable" },
      { status: 502, headers: { "content-type": "application/problem+json" } },
    );
  }
  const out = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!DROP_RESPONSE.has(key) && key !== "set-cookie") out.set(key, value);
  });
  for (const cookie of upstream.headers.getSetCookie()) out.append("set-cookie", cookie);
  return new Response(upstream.status === 204 ? null : upstream.body, { status: upstream.status, headers: out });
}

export { proxy as DELETE, proxy as GET, proxy as PATCH, proxy as POST, proxy as PUT };

import { describe, expect, it } from "vitest";
import { csp, thirdPartiesFromEnv } from "../middleware";

describe("csp", () => {
  it("allows the storage origin for uploads only in connect-src", () => {
    const value = csp("http://localhost:9000", false);
    expect(value).toContain("connect-src 'self' http://localhost:9000");
    expect(value).not.toContain("unsafe-eval");
    expect(value).toContain("frame-ancestors 'none'");
  });
  it("adds unsafe-eval only in development", () => {
    expect(csp(undefined, true)).toContain("'unsafe-eval'");
    expect(csp(undefined, false)).toContain("connect-src 'self';");
  });
  it("allows analytics and chat only when configured", () => {
    expect(csp(undefined, false)).not.toContain("posthog");
    expect(csp(undefined, false)).not.toContain("crisp");
    const third = thirdPartiesFromEnv({ NEXT_PUBLIC_POSTHOG_KEY: "phc_x", HB_CRISP_ENABLED: "1" });
    const value = csp(undefined, false, third);
    expect(value).toContain("connect-src 'self' https://eu.i.posthog.com https://client.crisp.chat wss://client.relay.crisp.chat");
    expect(value).toContain("https://eu-assets.i.posthog.com");
  });
});

describe("middleware", () => {
  it("sets HSTS only behind HTTPS and protects app routes", async () => {
    const { middleware } = await import("../middleware");
    const { NextRequest } = await import("next/server");
    const https = middleware(new NextRequest("http://web/login", { headers: { "x-forwarded-proto": "https" } }));
    expect(https.headers.get("strict-transport-security")).toContain("max-age=63072000");
    expect(https.headers.get("x-frame-options")).toBe("DENY");
    const http = middleware(new NextRequest("http://web/login"));
    expect(http.headers.get("strict-transport-security")).toBeNull();
    const app = middleware(new NextRequest("http://web/ops"));
    expect(app.status).toBe(307);
    expect(app.headers.get("location")).toContain("/login?next=%2Fops");
  });
  it("takes the language from marketing site links and drops the parameter", async () => {
    const { middleware } = await import("../middleware");
    const { NextRequest } = await import("next/server");
    const res = middleware(new NextRequest("http://web/register?lang=fr"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://web/register");
    expect(res.cookies.get("NEXT_LOCALE")?.value).toBe("fr");
    const unknown = middleware(new NextRequest("http://web/register?lang=xx"));
    expect(unknown.status).toBe(200);
  });
});

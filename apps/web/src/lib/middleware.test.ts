import { describe, expect, it } from "vitest";
import { csp } from "../middleware";

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
});

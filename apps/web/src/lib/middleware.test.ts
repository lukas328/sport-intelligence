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

import { describe, expect, it } from "vitest";
import { formatLatency, toHealthView } from "./health";

const base = { service: "handball-api", version: "0.1.0", env: "test" };

describe("toHealthView", () => {
  it("is unreachable without payload", () => {
    expect(toHealthView(null).state).toBe("unreachable");
  });

  it("is ok when all components are ok, sorted by fixed order", () => {
    const v = toHealthView({
      ...base,
      status: "ok",
      components: [
        { name: "storage", status: "ok", latency_ms: 3 },
        { name: "database", status: "ok", latency_ms: 1 },
        { name: "redis", status: "ok", latency_ms: 2 },
      ],
    });
    expect(v.state).toBe("ok");
    expect(v.components.map((c) => c.name)).toEqual(["database", "redis", "storage"]);
  });

  it("is degraded when one component fails", () => {
    const v = toHealthView({
      ...base,
      status: "degraded",
      components: [
        { name: "database", status: "ok", latency_ms: 1 },
        { name: "redis", status: "error", latency_ms: 2000, error: "TimeoutError" },
      ],
    });
    expect(v.state).toBe("degraded");
  });

  it("is degraded with no components", () => {
    expect(toHealthView({ ...base, status: "ok", components: [] }).state).toBe("degraded");
  });
});

describe("formatLatency", () => {
  it("formats with locale", () => {
    expect(formatLatency(1.234, "de-CH")).toBe("1.2 ms");
    expect(formatLatency(1234, "de-CH")).toMatch(/^1.234 ms$/);
  });
});

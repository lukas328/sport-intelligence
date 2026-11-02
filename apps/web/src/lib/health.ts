import type { ComponentStatus, Readiness } from "@handball/api-client";

export type OverallState = "ok" | "degraded" | "unreachable";

export interface HealthView {
  state: OverallState;
  version?: string;
  env?: string;
  components: ComponentStatus[];
}

const ORDER = ["database", "redis", "storage"];

/** Pure mapping from the API readiness payload (or a fetch failure) to what the status page shows. */
export function toHealthView(readiness: Readiness | null | undefined): HealthView {
  if (!readiness) return { state: "unreachable", components: [] };
  const components = [...readiness.components].sort(
    (a, b) => rank(a.name) - rank(b.name) || a.name.localeCompare(b.name),
  );
  const allOk = components.length > 0 && components.every((c) => c.status === "ok");
  return {
    state: allOk && readiness.status === "ok" ? "ok" : "degraded",
    version: readiness.version,
    env: readiness.env,
    components,
  };
}

function rank(name: string): number {
  const i = ORDER.indexOf(name);
  return i === -1 ? ORDER.length : i;
}

export function formatLatency(ms: number, locale: string): string {
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: ms < 10 ? 1 : 0 }).format(ms)} ms`;
}

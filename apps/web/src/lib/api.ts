import "server-only";
import { createApiClient, type Readiness } from "@handball/api-client";

/** Server-side base URL (inside docker compose: http://api:8000). */
export function apiBaseUrl(): string {
  return process.env.HB_API_INTERNAL_URL ?? "http://localhost:8000";
}

export async function fetchReadiness(timeoutMs = 3000): Promise<Readiness | null> {
  const client = createApiClient(apiBaseUrl());
  try {
    const { data, error, response } = await client.GET("/v1/health", {
      signal: AbortSignal.timeout(timeoutMs),
      cache: "no-store",
    });
    if (data) return data;
    // 503 still carries a Readiness body
    if (response.status === 503 && error) return error as Readiness;
    return null;
  } catch {
    return null;
  }
}

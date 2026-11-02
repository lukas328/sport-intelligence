import "server-only";
import { createApiClient, type Readiness } from "@handball/api-client";
import { cookies } from "next/headers";
import { apiBaseUrl } from "./api-base";

export { apiBaseUrl };

/** API client for server components, forwarding the user's cookies. */
export async function serverApi() {
  const store = await cookies();
  const cookie = store
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  return createApiClient(apiBaseUrl(), { headers: cookie ? { cookie } : {} });
}

export async function fetchReadiness(timeoutMs = 3000): Promise<Readiness | null> {
  const client = createApiClient(apiBaseUrl());
  try {
    const { data, error, response } = await client.GET("/v1/health", {
      signal: AbortSignal.timeout(timeoutMs),
      cache: "no-store",
    });
    if (data) return data;
    if (response.status === 503 && error) return error as Readiness;
    return null;
  } catch {
    return null;
  }
}

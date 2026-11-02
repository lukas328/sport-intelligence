import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type { components, paths };
export type Readiness = components["schemas"]["Readiness"];
export type ComponentStatus = components["schemas"]["ComponentStatus"];

/** Typed REST client generated from the API's OpenAPI schema (`make api-client`). */
export function createApiClient(baseUrl: string, init?: { fetch?: typeof fetch }) {
  return createClient<paths>({ baseUrl, credentials: "include", ...init });
}

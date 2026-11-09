import createClient, { type Middleware } from "openapi-fetch";
import type { components, paths } from "./schema";

export type { components, paths };
export type Schemas = components["schemas"];
export type Readiness = Schemas["Readiness"];
export type ComponentStatus = Schemas["ComponentStatus"];
export type Problem = {
  type?: string;
  title: string;
  status: number;
  detail?: string;
  errors?: { loc: (string | number)[]; msg: string; type: string }[];
};

export interface ClientOptions {
  fetch?: typeof fetch;
  headers?: Record<string, string>;
  /** Returns the CSRF token to send on unsafe requests (browser: from the hb_csrf cookie). */
  csrfToken?: () => string | undefined;
  /** Native apps: the session token, sent as bearer token instead of a cookie. */
  bearerToken?: () => string | undefined;
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** Typed REST client generated from the API's OpenAPI schema (`make api-client`). */
export function createApiClient(baseUrl: string, options: ClientOptions = {}) {
  const client = createClient<paths>({
    baseUrl,
    credentials: "include",
    ...(options.fetch ? { fetch: options.fetch } : {}),
    ...(options.headers ? { headers: options.headers } : {}),
  });
  if (options.csrfToken) {
    const getToken = options.csrfToken;
    const csrf: Middleware = {
      onRequest({ request }) {
        const token = getToken();
        if (token && UNSAFE.has(request.method)) request.headers.set("x-csrf-token", token);
        return request;
      },
    };
    client.use(csrf);
  }
  if (options.bearerToken) {
    const getBearer = options.bearerToken;
    client.use({
      onRequest({ request }) {
        const token = getBearer();
        if (token) request.headers.set("authorization", `Bearer ${token}`);
        return request;
      },
    });
  }
  return client;
}

export type ApiClient = ReturnType<typeof createApiClient>;

/** Problem type code, e.g. "email-taken" from "urn:handball-platform:problem:email-taken". */
export function problemCode(error: unknown): string | undefined {
  const type = (error as Problem | undefined)?.type;
  return type?.split(":").pop();
}

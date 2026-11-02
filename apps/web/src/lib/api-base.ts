/** Server-side base URL of the API (inside docker compose: http://api:8000). */
export function apiBaseUrl(): string {
  return process.env.HB_API_INTERNAL_URL ?? "http://localhost:8000";
}

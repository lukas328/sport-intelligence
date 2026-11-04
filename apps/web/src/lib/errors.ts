import { problemCode } from "@handball/api-client";

export const KNOWN_ERRORS = [
  "invalid-credentials",
  "email-taken",
  "weak-password",
  "terms-not-accepted",
  "rate-limited",
  "invalid-totp",
  "invalid-token",
  "jersey-number-taken",
  "two-factor-required",
  "invitation-email-mismatch",
  "invitation-revoked",
  "invitation-expired",
  "invitation-accepted",
  "forbidden",
  "not-found",
  "unsupported-image",
  "logo-too-large",
  "validation-error",
  "unauthenticated",
  "oauth-state",
  "oauth-failed",
  "oauth-email-unverified",
  "oauth-cancelled",
  "plan-required",
  "plan-limit-matches",
  "plan-limit-teams",
  "plan-limit-storage",
  "parent-needs-player",
  "parent-consent-required",
  "youth-protection",
  "last-admin",
  "invalid-format",
  "duplicate-number",
  "duplicate-name",
  "unknown-tag",
  "invalid-slide",
  "nothing-to-export",
  "too-many-slides",
  "image-too-large",
  "not-enough-scenes",
  "consent-missing",
  "invalid-voucher",
  "invoice-open",
  "assistant-budget",
  "assistant-unavailable",
  "file-too-large",
  "vision-unavailable",
  "paper-warnings",
  "paper-incomplete",
  "quota-reached",
  "already-member",
  "report-url-unsupported",
  "report-not-found",
  "report-unreadable",
  "report-empty",
  "report-unavailable",
] as const;

export type ErrorKey = (typeof KNOWN_ERRORS)[number] | "generic";

/** Maps an RFC 9457 problem body to a translation key under `errors.*`. */
export function errorKey(problem: unknown): ErrorKey {
  const code = problemCode(problem);
  return (KNOWN_ERRORS as readonly string[]).includes(code ?? "") ? (code as ErrorKey) : "generic";
}

/** Field errors from a 422 validation problem: { email: "value is not a valid email address" }. */
export function fieldErrors(problem: unknown): Record<string, string> {
  const errors = (problem as { errors?: { loc: (string | number)[]; msg: string }[] } | undefined)?.errors ?? [];
  const out: Record<string, string> = {};
  for (const e of errors) {
    const field = e.loc[e.loc.length - 1];
    if (typeof field === "string" && !(field in out)) out[field] = e.msg.replace(/^Value error, /, "");
  }
  return out;
}

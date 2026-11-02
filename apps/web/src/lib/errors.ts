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

/** Joins class names, skipping empty ones (the site has no tailwind-merge). */
export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

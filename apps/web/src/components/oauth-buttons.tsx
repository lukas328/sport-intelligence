import { getTranslations } from "next-intl/server";

const LABELS: Record<string, string> = { google: "Google", apple: "Apple" };

function GoogleIcon() {
  return (
    <svg aria-hidden viewBox="0 0 48 48" className="size-5">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.9 6.1C12.5 13.6 17.8 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.7 6c4.5-4.2 6.9-10.3 6.9-17.7z" />
      <path fill="#FBBC05" d="M10.6 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.7-6c-2.2 1.5-5 2.3-8.2 2.3-6.2 0-11.5-4.1-13.4-9.9l-7.9 6.1C6.6 42.6 14.6 48 24 48z" />
    </svg>
  );
}

function AppleIcon() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-5 fill-current">
      <path d="M16.4 12.6c0-2.6 2.1-3.8 2.2-3.9-1.2-1.8-3.1-2-3.7-2-1.6-.2-3.1.9-3.9.9-.8 0-2-.9-3.4-.9-1.7 0-3.3 1-4.2 2.6-1.8 3.1-.5 7.7 1.3 10.2.9 1.2 1.9 2.6 3.2 2.6 1.3-.1 1.8-.8 3.3-.8s2 .8 3.4.8c1.4 0 2.3-1.3 3.1-2.5 1-1.4 1.4-2.8 1.4-2.9-.1 0-2.7-1-2.7-4.1zM13.9 5c.7-.9 1.2-2 1-3.2-1 0-2.3.7-3 1.6-.7.8-1.3 2-1.1 3.1 1.2.1 2.3-.6 3.1-1.5z" />
    </svg>
  );
}

/** Links (not JS) to the API start endpoint: works without client JS and keeps the redirect same-origin. */
export async function OAuthButtons({ providers, next, invite }: { providers: string[]; next?: string; invite?: string }) {
  if (providers.length === 0) return null;
  const t = await getTranslations("auth");
  const query = new URLSearchParams();
  if (next) query.set("next", next);
  if (invite) query.set("invite", invite);
  const qs = query.toString() ? `?${query}` : "";
  return (
    <div className="space-y-3">
      {providers.map((p) => (
        <a
          key={p}
          href={`/v1/auth/oauth/${p}/start${qs}`}
          className="flex min-h-10 w-full items-center justify-center gap-2 rounded-md border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-surface"
        >
          {p === "google" ? <GoogleIcon /> : <AppleIcon />}
          {t("continueWith", { provider: LABELS[p] ?? p })}
        </a>
      ))}
      <p className="text-xs text-muted">{t("oauthTerms")}</p>
      <div className="flex items-center gap-3 text-xs text-muted" aria-hidden>
        <span className="h-px flex-1 bg-border" />
        {t("or")}
        <span className="h-px flex-1 bg-border" />
      </div>
    </div>
  );
}

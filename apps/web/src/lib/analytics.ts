/**
 * Product analytics (addendum 01, 4.12): PostHog (EU cloud or self-hosted), only after consent.
 * Without NEXT_PUBLIC_POSTHOG_KEY nothing is loaded and no banner is shown.
 */

export type CoreEvent = "signed_up" | "first_upload" | "analysis_viewed" | "presentation_held" | "player_active";

const KEY = "hb.consent.analytics";
type PostHog = { capture: (event: string, props?: Record<string, unknown>) => void; opt_out_capturing: () => void };
let client: PostHog | null = null;
let loading: Promise<PostHog | null> | null = null;

export function analyticsConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_POSTHOG_KEY);
}

export function consent(): "yes" | "no" | null {
  try {
    const v = window.localStorage.getItem(KEY);
    return v === "yes" || v === "no" ? v : null;
  } catch {
    return null;
  }
}

export function setConsent(v: "yes" | "no"): void {
  try {
    window.localStorage.setItem(KEY, v);
  } catch {
    /* private mode: ask again next time */
  }
  if (v === "yes") void load();
  else client?.opt_out_capturing();
}

async function load(): Promise<PostHog | null> {
  if (client || !analyticsConfigured() || consent() !== "yes") return client;
  loading ??= import("posthog-js").then(({ default: posthog }) => {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://eu.i.posthog.com",
      persistence: "localStorage",
      autocapture: false,
      capture_pageview: true,
      disable_session_recording: true,
      ip: false,
    });
    client = posthog as unknown as PostHog;
    return client;
  });
  return loading;
}

/** Core events for the activation and retention dashboard; a no-op without consent. */
export function track(event: CoreEvent, props?: Record<string, unknown>): void {
  if (typeof window === "undefined" || consent() !== "yes") return;
  void load().then((c) => c?.capture(event, props));
}

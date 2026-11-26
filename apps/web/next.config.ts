import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

// which build an error report comes from (lib/client-errors): the build time, or the commit when
// the build is given one (GIT_SHA); nothing about the build machine
const BUILD = process.env.GIT_SHA?.slice(0, 12) || new Date().toISOString().slice(0, 16);

const nextConfig: NextConfig = {
  output: "standalone",
  env: { NEXT_PUBLIC_BUILD: BUILD },
  poweredByHeader: false,
  devIndicators: false,
  reactStrictMode: true,
  transpilePackages: ["@handball/court", "@handball/api-client", "@handball/tactics", "@handball/client-core"],
  // fileURLToPath, not URL.pathname: on Windows pathname is "/C:/..." and Turbopack rejects it
  outputFileTracingRoot: fileURLToPath(new URL("../../", import.meta.url)),
  // the pictures of shared links and the Spielkarte read their fonts at runtime (K20)
  outputFileTracingIncludes: { "/s/[token]/og": ["./src/fonts/*.woff"], "/app/[orgId]/matches/[matchId]/spielkarte": ["./src/fonts/*.woff"] },
  // link previews of the chats read the tags in <head> only: Next's list of such clients plus
  // Telegram, Signal (fetches as WhatsApp), Threema, Viber and the embed services (K20, R2)
  htmlLimitedBots:
    /[\w-]+-Google|Google-[\w-]+|Chrome-Lighthouse|Slurp|DuckDuckBot|baiduspider|yandex|sogou|bitlybot|tumblr|vkShare|quora link preview|redditbot|ia_archiver|Bingbot|BingPreview|applebot|facebookexternalhit|facebookcatalog|Twitterbot|LinkedInBot|Slackbot|Discordbot|WhatsApp|SkypeUriPreview|Yeti|googleweblight|TelegramBot|Signal|Threema|Viber|Iframely|Embedly|meta-externalagent|Pinterestbot/i,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);

import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  devIndicators: false,
  reactStrictMode: true,
  transpilePackages: ["@handball/court", "@handball/api-client", "@handball/tactics", "@handball/client-core"],
  // fileURLToPath, not URL.pathname: on Windows pathname is "/C:/..." and Turbopack rejects it
  outputFileTracingRoot: fileURLToPath(new URL("../../", import.meta.url)),
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

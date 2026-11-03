import createMDX from "@next/mdx";
import remarkGfm from "remark-gfm";

/** Static marketing site (addendum 01, 4.13): exported to plain files, served by any web server. */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  poweredByHeader: false,
  reactStrictMode: true,
  images: { unoptimized: true },
  pageExtensions: ["ts", "tsx", "mdx"],
  transpilePackages: ["@handball/court"],
};

const withMDX = createMDX({ options: { remarkPlugins: [remarkGfm] } });

export default withMDX(nextConfig);

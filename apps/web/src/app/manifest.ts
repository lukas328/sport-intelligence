import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Handball Intelligence",
    short_name: "Handball",
    description: "Videoanalyse, Statistik und Taktik für Handballteams",
    start_url: "/app",
    display: "standalone",
    background_color: "#f7f8f6",
    theme_color: "#111316",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-512-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}

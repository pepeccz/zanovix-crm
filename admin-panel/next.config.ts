import type { NextConfig } from "next";
import { buildSecurityHeaders } from "./src/app/next.config.headers";

const nextConfig: NextConfig = {
  output: "standalone",
  // Internal admin panel: serve images as-is via /public, no optimization pipeline.
  // Avoids sharp/standalone gotchas with colormap PNGs and reduces image surface.
  images: {
    unoptimized: true,
  },
  async rewrites() {
    // Docker internal: service name `api` (zanovix-crm-api). Override with INTERNAL_API_URL for non-docker dev.
    const apiUrl = process.env.INTERNAL_API_URL || "http://api:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${apiUrl}/health`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: buildSecurityHeaders(),
      },
    ];
  },
};

export default nextConfig;

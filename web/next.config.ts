import type { NextConfig } from "next";

// The browser only talks to Next.js. Next.js forwards /api/* to the Python server on localhost
// (server/main.py), which is the only process that reads the team key.
const BRAIN = process.env.ATLAS_SERVER_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BRAIN}/api/:path*` }];
  },
};

export default nextConfig;

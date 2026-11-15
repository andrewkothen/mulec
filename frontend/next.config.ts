import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";
export default function config(phase: string): NextConfig {
  return phase === PHASE_DEVELOPMENT_SERVER
    ? {
        devIndicators: false,
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: "http://127.0.0.1:8765/api/:path*",
            },
          ];
        },
      }
    : { output: "export", devIndicators: false };
}

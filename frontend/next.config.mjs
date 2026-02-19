import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

initOpenNextCloudflareForDev();

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Image optimization for production backend domain
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'claude-agent-sdk-fastapi-sg4.tt-ai.org',
      },
    ],
  },

  // TypeScript configuration
  typescript: {
    // Enable TypeScript checking in production builds
    ignoreBuildErrors: false,
  },

  // React strict mode for better development experience
  reactStrictMode: true,
};

export default nextConfig;

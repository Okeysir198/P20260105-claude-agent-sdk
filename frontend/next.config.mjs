/** @type {import('next').NextConfig} */
const nextConfig = {
  // Image optimization for production backend domain
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'claude-agent-sdk-fastapi-sg4.tt-ai.org',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '7001',
      },
    ],
  },

  // TypeScript configuration
  typescript: {
    // Enable TypeScript checking in production builds
    ignoreBuildErrors: false,
  },

  // Output configuration
  output: 'standalone',

  // React strict mode for better development experience
  reactStrictMode: true,
};

export default nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React strict mode for better development experience
  reactStrictMode: true,

  // Configure image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },

  // API proxy rewrites for development
  // Note: WebSocket rewrites only work in Node.js server mode (next start), not serverless
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:7001';

    return [
      // HTTP API proxy
      {
        source: '/api/proxy/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
      // WebSocket proxy (works in `next dev` and `next start`, not Vercel serverless)
      {
        source: '/ws/:path*',
        destination: `${backendUrl}/api/v1/ws/:path*`,
      },
    ];
  },

  // Headers for CORS and security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },

  // TypeScript configuration
  typescript: {
    // Disable type checking during build for faster iteration
    ignoreBuildErrors: true,
  },
};

export default nextConfig;

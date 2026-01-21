/**
 * Custom Next.js server with WebSocket proxy support.
 *
 * This server proxies WebSocket connections to the backend,
 * allowing the frontend to be exposed via a single Cloudflare tunnel.
 *
 * Usage:
 *   Development: node server.js
 *   Production:  NODE_ENV=production node server.js
 *
 * Environment variables:
 *   PORT         - Server port (default: 7002)
 *   BACKEND_URL  - Backend URL (default: http://localhost:7001)
 */

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const next = require('next');
const { createServer } = require('http');

const dev = process.env.NODE_ENV !== 'production';
const port = parseInt(process.env.PORT || '7002', 10);
const backendUrl = process.env.BACKEND_URL || 'http://localhost:7001';

const app = next({ dev, port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const expressApp = express();
  const server = createServer(expressApp);

  // WebSocket proxy for /ws/* routes
  const wsProxy = createProxyMiddleware({
    target: backendUrl,
    changeOrigin: true,
    ws: true,
    pathRewrite: {
      '^/ws': '/api/v1/ws',  // /ws/chat -> /api/v1/ws/chat
    },
    logLevel: dev ? 'debug' : 'warn',
  });

  // API proxy for /api/proxy/* routes (REST endpoints)
  const apiProxy = createProxyMiddleware({
    target: backendUrl,
    changeOrigin: true,
    pathRewrite: {
      '^/api/proxy': '/api/v1',  // /api/proxy/sessions -> /api/v1/sessions
    },
    logLevel: dev ? 'debug' : 'warn',
  });

  // Apply proxies before Next.js handler
  expressApp.use('/ws', wsProxy);
  expressApp.use('/api/proxy', apiProxy);

  // Let Next.js handle everything else
  expressApp.all('*', (req, res) => handle(req, res));

  // CRITICAL: Handle WebSocket upgrade requests
  server.on('upgrade', (req, socket, head) => {
    if (req.url?.startsWith('/ws')) {
      wsProxy.upgrade(req, socket, head);
    } else {
      socket.destroy();
    }
  });

  server.listen(port, () => {
    console.log(`> Ready on http://localhost:${port}`);
    console.log(`> Backend proxy: ${backendUrl}`);
    console.log(`> WebSocket: /ws/* -> ${backendUrl}/api/v1/ws/*`);
    console.log(`> API: /api/proxy/* -> ${backendUrl}/api/v1/*`);
  });
});

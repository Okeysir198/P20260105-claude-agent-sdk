/**
 * Custom Next.js server.
 *
 * This is a minimal server for development. The frontend connects
 * directly to the backend for API and WebSocket connections.
 *
 * Usage:
 *   Development: node server.js
 *   Production:  NODE_ENV=production node server.js
 *
 * Environment variables:
 *   PORT - Server port (default: 7002)
 */

const express = require('express');
const next = require('next');
const { createServer } = require('http');

const dev = process.env.NODE_ENV !== 'production';
const port = parseInt(process.env.PORT || '7002', 10);

const app = next({ dev, port });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const expressApp = express();
  const server = createServer(expressApp);

  // Let Next.js handle all requests
  expressApp.all('*', (req, res) => handle(req, res));

  server.listen(port, () => {
    console.log(`> Ready on http://localhost:${port}`);
    console.log(`> Frontend connects directly to backend API`);
  });
});

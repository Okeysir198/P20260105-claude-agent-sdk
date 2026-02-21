/**
 * Prepare for Cloudflare build:
 * 1. Rename proxy.ts → middleware.ts (OpenNext doesn't support proxy.ts yet).
 * 2. Hide .env.local so .env.production takes precedence during build.
 */
import { readFileSync, writeFileSync, renameSync, existsSync } from 'fs';

const proxyPath = 'proxy.ts';
const middlewarePath = 'middleware.ts';
const envLocalPath = '.env.local';
const envLocalBackup = '.env.local.bak';

if (existsSync(proxyPath)) {
  let content = readFileSync(proxyPath, 'utf-8');
  content = content.replace(
    /export async function proxy\(/,
    'export async function middleware('
  );
  writeFileSync(middlewarePath, content);
  renameSync(proxyPath, 'proxy.ts.bak');
  console.log('cf-prepare: proxy.ts → middleware.ts (with function rename)');
}

// Hide .env.local so Next.js uses .env.production for the CF build
if (existsSync(envLocalPath)) {
  renameSync(envLocalPath, envLocalBackup);
  console.log('cf-prepare: .env.local hidden (using .env.production for build)');
}

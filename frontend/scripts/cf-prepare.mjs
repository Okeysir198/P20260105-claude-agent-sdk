/**
 * Prepare for Cloudflare build:
 * Rename proxy.ts → middleware.ts (OpenNext doesn't support proxy.ts yet).
 * Also rename the exported function from 'proxy' to 'middleware'.
 */
import { readFileSync, writeFileSync, renameSync, existsSync } from 'fs';

const proxyPath = 'proxy.ts';
const middlewarePath = 'middleware.ts';

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

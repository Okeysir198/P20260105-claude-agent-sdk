/**
 * Restore after Cloudflare build:
 * Rename middleware.ts back to proxy.ts.
 */
import { unlinkSync, renameSync, existsSync } from 'fs';

const middlewarePath = 'middleware.ts';
const backupPath = 'proxy.ts.bak';
const proxyPath = 'proxy.ts';

if (existsSync(backupPath)) {
  renameSync(backupPath, proxyPath);
  if (existsSync(middlewarePath)) {
    unlinkSync(middlewarePath);
  }
  console.log('cf-restore: restored proxy.ts from backup');
}

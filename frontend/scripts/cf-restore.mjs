/**
 * Restore after Cloudflare build:
 * 1. Rename middleware.ts back to proxy.ts.
 * 2. Restore .env.local from backup.
 */
import { unlinkSync, renameSync, existsSync } from 'fs';

const middlewarePath = 'middleware.ts';
const backupPath = 'proxy.ts.bak';
const proxyPath = 'proxy.ts';
const envLocalPath = '.env.local';
const envLocalBackup = '.env.local.bak';

if (existsSync(backupPath)) {
  renameSync(backupPath, proxyPath);
  if (existsSync(middlewarePath)) {
    unlinkSync(middlewarePath);
  }
  console.log('cf-restore: restored proxy.ts from backup');
}

// Restore .env.local
if (existsSync(envLocalBackup)) {
  renameSync(envLocalBackup, envLocalPath);
  console.log('cf-restore: restored .env.local');
}

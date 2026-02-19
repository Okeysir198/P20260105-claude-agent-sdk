/**
 * JWT Utilities for Token Creation and Management
 *
 * Provides common JWT functionality used by auth routes.
 * Uses HMAC-SHA256 to derive JWT secret from API_KEY (same as backend).
 * Uses Web Crypto API for edge runtime compatibility (Cloudflare Pages).
 */
import { SignJWT } from 'jose';
import { v4 as uuidv4 } from 'uuid';

/**
 * JWT configuration (must match backend)
 */
export const JWT_CONFIG = {
  algorithm: 'HS256' as const,
  accessTokenExpireMinutes: 30,
  refreshTokenExpireDays: 7,
  issuer: 'claude-agent-sdk',
  audience: 'claude-agent-sdk-users',
};

/**
 * Convert an ArrayBuffer to hex string
 */
function bufferToHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Derive JWT secret from API_KEY using HMAC-SHA256 (same as backend).
 * Uses Web Crypto API for edge runtime compatibility.
 */
export async function deriveJwtSecret(apiKey: string): Promise<string> {
  const salt = 'claude-agent-sdk-jwt-v1';
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(salt),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(apiKey));
  return bufferToHex(signature);
}

/**
 * Derive user ID from API key (same logic as backend).
 * Uses Web Crypto API for edge runtime compatibility.
 */
export async function getUserIdFromApiKey(apiKey: string): Promise<string> {
  const encoder = new TextEncoder();
  const hash = await crypto.subtle.digest('SHA-256', encoder.encode(apiKey));
  return bufferToHex(hash).substring(0, 32);
}

/**
 * Create a JWT token
 */
export async function createToken(
  secret: Uint8Array,
  userId: string,
  type: 'access' | 'refresh' | 'user_identity',
  expiresIn: number,
  additionalClaims?: Record<string, string>
): Promise<{ token: string; jti: string; expiresIn: number }> {
  const jti = uuidv4();
  const now = Math.floor(Date.now() / 1000);
  const exp = now + expiresIn;

  const token = await new SignJWT({
    sub: userId,
    jti,
    type,
    ...additionalClaims,
  })
    .setProtectedHeader({ alg: JWT_CONFIG.algorithm, typ: 'JWT' })
    .setIssuedAt(now)
    .setExpirationTime(exp)
    .setIssuer(JWT_CONFIG.issuer)
    .setAudience(JWT_CONFIG.audience)
    .sign(secret);

  return { token, jti, expiresIn };
}

/**
 * Get access token expiry in seconds
 */
export function getAccessTokenExpiry(): number {
  return JWT_CONFIG.accessTokenExpireMinutes * 60;
}

/**
 * Get refresh token expiry in seconds
 */
export function getRefreshTokenExpiry(): number {
  return JWT_CONFIG.refreshTokenExpireDays * 24 * 60 * 60;
}

/**
 * Server-side authentication utilities shared across API routes.
 * Handles session token refresh using refresh cookies.
 */
import { cookies } from 'next/headers';
import { jwtVerify } from 'jose';
import { verifySession, setSessionCookie, SESSION_COOKIE, REFRESH_COOKIE } from '@/lib/session';
import { deriveJwtSecret, createToken, getAccessTokenExpiry, getRefreshTokenExpiry } from '@/lib/jwt-utils';

/**
 * Attempt to refresh the session token using a refresh token.
 * Creates new access and refresh tokens, and updates session cookies.
 *
 * @param refreshToken - The refresh JWT token
 * @param apiKey - The server API key used to derive the JWT secret
 * @returns The new session token if successful, null otherwise
 */
export async function tryRefreshSession(
  refreshToken: string,
  apiKey: string,
): Promise<string | null> {
  try {
    const jwtSecret = deriveJwtSecret(apiKey);
    const secret = new TextEncoder().encode(jwtSecret);

    const { payload } = await jwtVerify(refreshToken, secret, {
      issuer: 'claude-agent-sdk',
      audience: 'claude-agent-sdk-users',
    });

    if (payload.type !== 'refresh') {
      return null;
    }

    const userId = payload.sub as string;

    const additionalClaims: Record<string, string> = {};
    if (payload.user_id) additionalClaims.user_id = payload.user_id as string;
    if (payload.username) additionalClaims.username = payload.username as string;
    if (payload.role) additionalClaims.role = payload.role as string;
    if (payload.full_name) additionalClaims.full_name = payload.full_name as string;

    const accessTokenExpiry = getAccessTokenExpiry();
    const { token: newSessionToken } = await createToken(
      secret,
      userId,
      'user_identity',
      accessTokenExpiry,
      additionalClaims,
    );

    const refreshTokenExpiry = getRefreshTokenExpiry();
    const { token: newRefreshToken } = await createToken(
      secret,
      userId,
      'refresh',
      refreshTokenExpiry,
      additionalClaims,
    );

    await setSessionCookie(newSessionToken, newRefreshToken);
    return newSessionToken;
  } catch {
    return null;
  }
}

/**
 * Resolves a valid session token from cookies, refreshing if expired.
 *
 * @param apiKey - The server API key
 * @returns The valid session token, or undefined if no valid session exists
 */
export async function resolveSessionToken(apiKey: string): Promise<string | undefined> {
  const cookieStore = await cookies();
  let sessionToken = cookieStore.get(SESSION_COOKIE)?.value;

  if (!sessionToken) {
    return undefined;
  }

  const session = await verifySession(sessionToken);
  if (session) {
    return sessionToken;
  }

  // Session expired, try to refresh
  const refreshToken = cookieStore.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) {
    return undefined;
  }

  const newToken = await tryRefreshSession(refreshToken, apiKey);
  return newToken ?? undefined;
}

import { cookies } from 'next/headers';
import { jwtVerify } from 'jose';
import { verifySession, setSessionCookie, SESSION_COOKIE, REFRESH_COOKIE } from '@/lib/session';
import { deriveJwtSecret, createToken, getAccessTokenExpiry, getRefreshTokenExpiry } from '@/lib/jwt-utils';

export async function tryRefreshSession(
  refreshToken: string,
  apiKey: string,
): Promise<string | null> {
  try {
    const jwtSecret = await deriveJwtSecret(apiKey);
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

export async function resolveSessionToken(apiKey: string): Promise<string | undefined> {
  const cookieStore = await cookies();
  const sessionToken = cookieStore.get(SESSION_COOKIE)?.value;

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

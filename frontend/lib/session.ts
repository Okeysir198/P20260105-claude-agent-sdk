import { cookies } from 'next/headers';
import { jwtVerify } from 'jose';
import { deriveJwtSecret } from './jwt-utils';

export const SESSION_COOKIE = 'claude_agent_session';
export const REFRESH_COOKIE = 'claude_agent_refresh';

export interface SessionPayload {
  user_id: string;
  username: string;
  full_name: string | null;
  role: 'admin' | 'user';
}

/**
 * Get the current session from the cookie
 */
export async function getSession(): Promise<SessionPayload | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;

  if (!token) {
    return null;
  }

  return verifySession(token);
}

/**
 * Set the session cookie (server-side)
 */
export async function setSessionCookie(token: string, refreshToken?: string): Promise<void> {
  const cookieStore = await cookies();

  // Set access token cookie (30 min)
  cookieStore.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 30 * 60, // 30 minutes
  });

  // Set refresh token cookie (7 days)
  if (refreshToken) {
    cookieStore.set(REFRESH_COOKIE, refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 7 * 24 * 60 * 60, // 7 days
    });
  }
}

/**
 * Clear session cookies (server-side)
 */
export async function clearSessionCookie(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE);
  cookieStore.delete(REFRESH_COOKIE);
}

/**
 * Verify a session token and extract payload
 */
export async function verifySession(token: string): Promise<SessionPayload | null> {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    console.error('API_KEY not configured');
    return null;
  }

  try {
    const jwtSecret = await deriveJwtSecret(apiKey);
    const secret = new TextEncoder().encode(jwtSecret);

    const { payload } = await jwtVerify(token, secret, {
      issuer: 'claude-agent-sdk',
      audience: 'claude-agent-sdk-users',
    });

    // Extract user info from token
    return {
      user_id: payload.user_id as string,
      username: payload.username as string,
      full_name: (payload.full_name as string) || null,
      role: payload.role as 'admin' | 'user',
    };
  } catch (error) {
    console.error('Session verification failed:', error);
    return null;
  }
}

/**
 * Get refresh token from cookie
 */
export async function getRefreshToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(REFRESH_COOKIE)?.value || null;
}

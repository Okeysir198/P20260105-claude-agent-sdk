/**
 * JWT Token Refresh Route
 *
 * Validates refresh token and creates new tokens.
 * Uses secret derived from API_KEY (same as backend).
 */
import { NextRequest, NextResponse } from 'next/server';
import { jwtVerify } from 'jose';
import { JWT_CONFIG, deriveJwtSecret, createTokenPair } from '@/lib/jwt-utils';

const API_KEY = process.env.API_KEY;

const USER_CLAIM_KEYS = ['user_id', 'username', 'role', 'full_name'] as const;

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!API_KEY) {
    console.error('API_KEY environment variable not configured');
    return NextResponse.json(
      { error: 'Server configuration error: API_KEY not set' },
      { status: 500 }
    );
  }

  try {
    const body = await request.json();
    const refreshToken = body.refresh_token;

    if (!refreshToken) {
      return NextResponse.json(
        { error: 'refresh_token is required' },
        { status: 400 }
      );
    }

    const jwtSecret = await deriveJwtSecret(API_KEY);
    const secret = new TextEncoder().encode(jwtSecret);

    let payload;
    try {
      const result = await jwtVerify(refreshToken, secret, {
        issuer: JWT_CONFIG.issuer,
        audience: JWT_CONFIG.audience,
      });
      payload = result.payload;
    } catch (err) {
      console.error('Refresh token validation failed:', err);
      return NextResponse.json(
        { error: 'Invalid or expired refresh token' },
        { status: 401 }
      );
    }

    if (payload.type !== 'refresh') {
      return NextResponse.json(
        { error: 'Invalid token type' },
        { status: 401 }
      );
    }

    const userId = payload.sub as string;

    // Preserve user claims from refresh token
    const additionalClaims: Record<string, string> = {};
    for (const key of USER_CLAIM_KEYS) {
      if (payload[key]) additionalClaims[key] = payload[key] as string;
    }

    const tokenPair = await createTokenPair(API_KEY, userId, additionalClaims);

    console.log(`JWT tokens refreshed for user ${userId}`);

    return NextResponse.json(tokenPair);
  } catch (error) {
    console.error('Token refresh failed:', error);
    return NextResponse.json(
      { error: 'Failed to refresh tokens' },
      { status: 500 }
    );
  }
}

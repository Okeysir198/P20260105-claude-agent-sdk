/**
 * JWT Token Creation Route
 *
 * Creates JWT tokens using a secret derived from API_KEY.
 * Includes user identity claims from session if available.
 */
import { NextRequest, NextResponse } from 'next/server';
import {
  JWT_CONFIG,
  deriveJwtSecret,
  getUserIdFromApiKey,
  createToken,
  getAccessTokenExpiry,
  getRefreshTokenExpiry,
} from '@/lib/jwt-utils';
import { getSession } from '@/lib/session';

const API_KEY = process.env.API_KEY;

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!API_KEY) {
    console.error('API_KEY environment variable not configured');
    return NextResponse.json(
      { error: 'Server configuration error: API_KEY not set' },
      { status: 500 }
    );
  }

  try {
    // Get user session if available
    const session = await getSession();

    const jwtSecret = await deriveJwtSecret(API_KEY);
    const secret = new TextEncoder().encode(jwtSecret);

    // Use session user_id if available, otherwise derive from API_KEY
    const userId = session?.user_id || await getUserIdFromApiKey(API_KEY);

    // Build additional claims with user info
    const additionalClaims: Record<string, string> = {};
    if (session) {
      additionalClaims.user_id = session.user_id;
      additionalClaims.username = session.username;
      additionalClaims.role = session.role;
      additionalClaims.full_name = session.full_name || '';
    }

    // Create user identity token for WebSocket (30 minutes)
    // Backend expects 'user_identity' type token for WebSocket authentication
    const accessTokenExpiry = getAccessTokenExpiry();
    const { token: accessToken, expiresIn } = await createToken(
      secret,
      userId,
      'user_identity',
      accessTokenExpiry,
      additionalClaims
    );

    // Create refresh token (7 days) - include user claims for preservation during refresh
    const refreshTokenExpiry = getRefreshTokenExpiry();
    const { token: refreshToken } = await createToken(
      secret,
      userId,
      'refresh',
      refreshTokenExpiry,
      additionalClaims
    );

    console.log(`JWT tokens created for user ${session?.username || userId}`);

    return NextResponse.json({
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: 'bearer',
      expires_in: expiresIn,
      user_id: userId,
      username: session?.username,
    });
  } catch (error) {
    console.error('Token creation failed:', error);
    return NextResponse.json(
      { error: 'Failed to create tokens' },
      { status: 500 }
    );
  }
}

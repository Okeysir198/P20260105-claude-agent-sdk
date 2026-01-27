/**
 * JWT Token Creation Route
 *
 * Creates JWT tokens using a secret derived from API_KEY.
 * No backend call needed - tokens are created locally.
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

// Server-only environment variables
const API_KEY = process.env.API_KEY;

export async function POST(request: NextRequest): Promise<NextResponse> {
  // Validate server configuration
  if (!API_KEY) {
    console.error('API_KEY environment variable not configured');
    return NextResponse.json(
      { error: 'Server configuration error: API_KEY not set' },
      { status: 500 }
    );
  }

  try {
    // Derive JWT secret from API_KEY (same derivation as backend)
    const jwtSecret = deriveJwtSecret(API_KEY);
    const secret = new TextEncoder().encode(jwtSecret);
    const userId = getUserIdFromApiKey(API_KEY);

    // Create access token (30 minutes)
    const accessTokenExpiry = getAccessTokenExpiry();
    const { token: accessToken, expiresIn } = await createToken(
      secret,
      userId,
      'access',
      accessTokenExpiry
    );

    // Create refresh token (7 days)
    const refreshTokenExpiry = getRefreshTokenExpiry();
    const { token: refreshToken } = await createToken(
      secret,
      userId,
      'refresh',
      refreshTokenExpiry
    );

    console.log(`JWT tokens created for user ${userId}`);

    return NextResponse.json({
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: 'bearer',
      expires_in: expiresIn,
      user_id: userId,
    });
  } catch (error) {
    console.error('Token creation failed:', error);
    return NextResponse.json(
      { error: 'Failed to create tokens' },
      { status: 500 }
    );
  }
}

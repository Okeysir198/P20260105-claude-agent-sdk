/**
 * JWT Token Refresh Route
 *
 * Validates refresh token and creates new tokens.
 * Uses secret derived from API_KEY (same as backend).
 */
import { NextRequest, NextResponse } from 'next/server';
import { SignJWT, jwtVerify } from 'jose';
import { v4 as uuidv4 } from 'uuid';
import { createHmac } from 'crypto';

// Server-only environment variables
const API_KEY = process.env.API_KEY;

/**
 * Derive JWT secret from API_KEY using HMAC-SHA256 (same as backend)
 */
function deriveJwtSecret(apiKey: string): string {
  const salt = 'claude-agent-sdk-jwt-v1';
  return createHmac('sha256', salt).update(apiKey).digest('hex');
}

// JWT configuration (must match backend)
const JWT_CONFIG = {
  algorithm: 'HS256' as const,
  accessTokenExpireMinutes: 30,
  refreshTokenExpireDays: 7,
  issuer: 'claude-agent-sdk',
  audience: 'claude-agent-sdk-users',
};

/**
 * Create a JWT token
 */
async function createToken(
  secret: Uint8Array,
  userId: string,
  type: 'access' | 'refresh',
  expiresIn: number
): Promise<{ token: string; jti: string; expiresIn: number }> {
  const jti = uuidv4();
  const now = Math.floor(Date.now() / 1000);
  const exp = now + expiresIn;

  const token = await new SignJWT({
    sub: userId,
    jti,
    type,
  })
    .setProtectedHeader({ alg: JWT_CONFIG.algorithm, typ: 'JWT' })
    .setIssuedAt(now)
    .setExpirationTime(exp)
    .setIssuer(JWT_CONFIG.issuer)
    .setAudience(JWT_CONFIG.audience)
    .sign(secret);

  return { token, jti, expiresIn };
}

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
    // Get refresh token from request body
    const body = await request.json();
    const refreshToken = body.refresh_token;

    if (!refreshToken) {
      return NextResponse.json(
        { error: 'refresh_token is required' },
        { status: 400 }
      );
    }

    // Derive JWT secret from API_KEY (same derivation as backend)
    const jwtSecret = deriveJwtSecret(API_KEY);
    const secret = new TextEncoder().encode(jwtSecret);

    // Verify refresh token
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

    // Check token type
    if (payload.type !== 'refresh') {
      return NextResponse.json(
        { error: 'Invalid token type' },
        { status: 401 }
      );
    }

    const userId = payload.sub as string;

    // Create new access token (30 minutes)
    const accessTokenExpiry = JWT_CONFIG.accessTokenExpireMinutes * 60;
    const { token: accessToken, expiresIn } = await createToken(
      secret,
      userId,
      'access',
      accessTokenExpiry
    );

    // Create new refresh token (7 days)
    const refreshTokenExpiry = JWT_CONFIG.refreshTokenExpireDays * 24 * 60 * 60;
    const { token: newRefreshToken } = await createToken(
      secret,
      userId,
      'refresh',
      refreshTokenExpiry
    );

    console.log(`JWT tokens refreshed for user ${userId}`);

    return NextResponse.json({
      access_token: accessToken,
      refresh_token: newRefreshToken,
      token_type: 'bearer',
      expires_in: expiresIn,
      user_id: userId,
    });
  } catch (error) {
    console.error('Token refresh failed:', error);
    return NextResponse.json(
      { error: 'Failed to refresh tokens' },
      { status: 500 }
    );
  }
}

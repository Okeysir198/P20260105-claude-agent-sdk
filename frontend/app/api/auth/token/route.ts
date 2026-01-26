/**
 * JWT Token Creation Route
 *
 * Creates JWT tokens using a secret derived from API_KEY.
 * No backend call needed - tokens are created locally.
 */
import { NextRequest, NextResponse } from 'next/server';
import { SignJWT } from 'jose';
import { v4 as uuidv4 } from 'uuid';
import { createHash, createHmac } from 'crypto';

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
 * Derive user ID from API key (same logic as backend)
 */
function getUserIdFromApiKey(apiKey: string): string {
  return createHash('sha256').update(apiKey).digest('hex').substring(0, 32);
}

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
    // Derive JWT secret from API_KEY (same derivation as backend)
    const jwtSecret = deriveJwtSecret(API_KEY);
    const secret = new TextEncoder().encode(jwtSecret);
    const userId = getUserIdFromApiKey(API_KEY);

    // Create access token (30 minutes)
    const accessTokenExpiry = JWT_CONFIG.accessTokenExpireMinutes * 60;
    const { token: accessToken, expiresIn } = await createToken(
      secret,
      userId,
      'access',
      accessTokenExpiry
    );

    // Create refresh token (7 days)
    const refreshTokenExpiry = JWT_CONFIG.refreshTokenExpireDays * 24 * 60 * 60;
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

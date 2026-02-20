/**
 * JWT Token Creation Route
 *
 * Creates JWT tokens using a secret derived from API_KEY.
 * Includes user identity claims from session if available.
 */
import { NextRequest, NextResponse } from 'next/server';
import { getUserIdFromApiKey, createTokenPair } from '@/lib/jwt-utils';
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
    const session = await getSession();
    const userId = session?.user_id || await getUserIdFromApiKey(API_KEY);

    const additionalClaims: Record<string, string> = {};
    if (session) {
      additionalClaims.user_id = session.user_id;
      additionalClaims.username = session.username;
      additionalClaims.role = session.role;
      additionalClaims.full_name = session.full_name || '';
    }

    const tokenPair = await createTokenPair(API_KEY, userId, additionalClaims);

    console.log(`JWT tokens created for user ${session?.username || userId}`);

    return NextResponse.json({
      ...tokenPair,
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

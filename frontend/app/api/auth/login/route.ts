/**
 * Login API Route
 *
 * Authenticates user against backend and sets session cookie.
 */
import { NextRequest, NextResponse } from 'next/server';
import { setSessionCookie } from '@/lib/session';

const API_KEY = process.env.API_KEY;
const BACKEND_API_URL = process.env.BACKEND_API_URL;

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!API_KEY || !BACKEND_API_URL) {
    return NextResponse.json(
      { success: false, error: 'Server configuration error' },
      { status: 500 }
    );
  }

  try {
    const body = await request.json();
    const { username, password } = body;

    if (!username || !password) {
      return NextResponse.json(
        { success: false, error: 'Username and password required' },
        { status: 400 }
      );
    }

    // Call backend login endpoint
    // Note: BACKEND_API_URL already includes /api/v1
    const response = await fetch(`${BACKEND_API_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      return NextResponse.json(
        { success: false, error: data.error || 'Login failed' },
        { status: response.status }
      );
    }

    // Set session cookie with user token
    await setSessionCookie(data.token, data.refresh_token);

    return NextResponse.json({
      success: true,
      user: data.user,
    });
  } catch (error) {
    console.error('Login error:', error);
    return NextResponse.json(
      { success: false, error: 'Login failed' },
      { status: 500 }
    );
  }
}

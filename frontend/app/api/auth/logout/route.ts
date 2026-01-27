/**
 * Logout API Route
 *
 * Clears session cookies.
 */
import { NextResponse } from 'next/server';
import { clearSessionCookie } from '@/lib/session';

export async function POST(): Promise<NextResponse> {
  try {
    await clearSessionCookie();
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Logout error:', error);
    return NextResponse.json(
      { success: false, error: 'Logout failed' },
      { status: 500 }
    );
  }
}

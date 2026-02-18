import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;

  // Get OAuth callback parameters
  const code = searchParams.get('code');
  const state = searchParams.get('state');
  const error = searchParams.get('error');

  // Get the production URL from environment or use the request's origin
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || request.nextUrl.origin;

  console.log('Gmail OAuth callback received:', { code: !!code, state: !!state, error, baseUrl });

  if (error) {
    // User denied authorization or there was an error
    console.error('Gmail OAuth error:', error);
    return NextResponse.redirect(`${baseUrl}/profile?error=gmail_oauth_error`);
  }

  if (!code || !state) {
    console.error('Missing required OAuth parameters');
    return NextResponse.redirect(`${baseUrl}/profile?error=missing_oauth_params`);
  }

  // Forward the callback to the backend with proper auth
  try {
    const backendUrl = process.env.BACKEND_API_URL;

    if (!backendUrl) {
      console.error('BACKEND_API_URL environment variable is not set');
      return NextResponse.redirect(`${baseUrl}/profile?error=missing_backend_config`);
    }

    // Build URL with query parameters
    const callbackUrl = new URL(`${backendUrl}/email/gmail/callback`);
    callbackUrl.searchParams.set('code', code);
    callbackUrl.searchParams.set('state', state);

    const response = await fetch(callbackUrl.toString(), {
      method: 'GET',
      headers: {
        // Forward cookies to maintain session
        'Cookie': request.headers.get('cookie') || '',
        'X-API-Key': process.env.API_KEY || '',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend callback error:', response.status, errorText);
      return NextResponse.redirect(`${baseUrl}/profile?error=backend_callback_failed`);
    }

    const data = await response.json();
    console.log('Backend callback success:', data);

    // Redirect to profile page with success indicator
    return NextResponse.redirect(`${baseUrl}/profile?email=gmail&status=connected`);

  } catch (error) {
    console.error('Error forwarding to backend:', error);
    return NextResponse.redirect(`${baseUrl}/profile?error=callback_forward_failed`);
  }
}

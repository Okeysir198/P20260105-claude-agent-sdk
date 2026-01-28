/**
 * API Proxy Route
 *
 * Proxies requests to the backend API, adding the API key server-side.
 * This hides the API key from the browser.
 *
 * Usage: /api/proxy/sessions → Backend /api/v1/sessions
 */
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { verifySession, setSessionCookie, SESSION_COOKIE, REFRESH_COOKIE } from '@/lib/session';
import { deriveJwtSecret, createToken, getAccessTokenExpiry, getRefreshTokenExpiry } from '@/lib/jwt-utils';
import { jwtVerify } from 'jose';

// Server-only environment variables (not prefixed with NEXT_PUBLIC_)
const API_KEY = process.env.API_KEY;
const BACKEND_API_URL = process.env.BACKEND_API_URL;

/**
 * Attempt to refresh the session token using the refresh cookie.
 * Returns the new session token if successful, null otherwise.
 */
async function tryRefreshSession(refreshToken: string): Promise<string | null> {
  if (!API_KEY) return null;

  try {
    const jwtSecret = deriveJwtSecret(API_KEY);
    const secret = new TextEncoder().encode(jwtSecret);

    // Verify refresh token
    const { payload } = await jwtVerify(refreshToken, secret, {
      issuer: 'claude-agent-sdk',
      audience: 'claude-agent-sdk-users',
    });

    if (payload.type !== 'refresh') {
      return null;
    }

    const userId = payload.sub as string;

    // Preserve user claims from refresh token
    const additionalClaims: Record<string, string> = {};
    if (payload.user_id) additionalClaims.user_id = payload.user_id as string;
    if (payload.username) additionalClaims.username = payload.username as string;
    if (payload.role) additionalClaims.role = payload.role as string;
    if (payload.full_name) additionalClaims.full_name = payload.full_name as string;

    // Create new session token (user_identity type)
    const accessTokenExpiry = getAccessTokenExpiry();
    const { token: newSessionToken } = await createToken(
      secret,
      userId,
      'user_identity',
      accessTokenExpiry,
      additionalClaims
    );

    // Create new refresh token
    const refreshTokenExpiry = getRefreshTokenExpiry();
    const { token: newRefreshToken } = await createToken(
      secret,
      userId,
      'refresh',
      refreshTokenExpiry,
      additionalClaims
    );

    // Update cookies with new tokens
    await setSessionCookie(newSessionToken, newRefreshToken);

    console.log(`Session refreshed for user ${userId} via proxy`);
    return newSessionToken;
  } catch (error) {
    console.error('Failed to refresh session in proxy:', error);
    return null;
  }
}

/**
 * Forward a request to the backend with API key authentication
 */
async function proxyRequest(
  request: NextRequest,
  params: { path: string[] }
): Promise<NextResponse> {
  // Validate server configuration
  if (!API_KEY) {
    console.error('API_KEY environment variable not configured');
    return NextResponse.json(
      { error: 'Server configuration error: API_KEY not set' },
      { status: 500 }
    );
  }

  if (!BACKEND_API_URL) {
    console.error('BACKEND_API_URL environment variable not configured');
    return NextResponse.json(
      { error: 'Server configuration error: BACKEND_API_URL not set' },
      { status: 500 }
    );
  }

  // Build the target URL
  const pathSegments = params.path;
  const targetPath = pathSegments.join('/');
  const searchParams = request.nextUrl.searchParams.toString();
  const queryString = searchParams ? `?${searchParams}` : '';
  const targetUrl = `${BACKEND_API_URL}/${targetPath}${queryString}`;

  // Build headers, forwarding most from the original request
  const headers = new Headers();

  // Forward relevant headers from the original request
  const headersToForward = [
    'content-type',
    'accept',
    'accept-language',
    'cache-control',
    'pragma',
  ];

  for (const headerName of headersToForward) {
    const headerValue = request.headers.get(headerName);
    if (headerValue) {
      headers.set(headerName, headerValue);
    }
  }

  // Add the API key header (this is the main purpose of the proxy)
  headers.set('X-API-Key', API_KEY);

  // Add user token header if session exists and is valid
  const cookieStore = await cookies();
  let sessionToken = cookieStore.get(SESSION_COOKIE)?.value;

  if (sessionToken) {
    // Verify the session token is still valid
    const session = await verifySession(sessionToken);

    if (!session) {
      // Session expired, try to refresh using refresh cookie
      const refreshToken = cookieStore.get(REFRESH_COOKIE)?.value;

      if (refreshToken) {
        const newToken = await tryRefreshSession(refreshToken);
        if (newToken) {
          sessionToken = newToken;
        } else {
          // Refresh failed, clear the invalid token
          sessionToken = undefined;
        }
      } else {
        // No refresh token, clear the invalid session token
        sessionToken = undefined;
      }
    }

    if (sessionToken) {
      headers.set('X-User-Token', sessionToken);
    }
  }

  // Get request body for POST/PUT/PATCH requests
  let body: string | undefined;
  if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
    try {
      body = await request.text();
    } catch {
      // No body or error reading body
    }
  }

  try {
    // Forward the request to the backend
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
    });

    // Get response body
    const responseBody = await response.text();

    // Build response headers to forward back to client
    const responseHeaders = new Headers();

    // Forward relevant response headers
    const responseHeadersToForward = [
      'content-type',
      'cache-control',
      'etag',
      'last-modified',
    ];

    for (const headerName of responseHeadersToForward) {
      const headerValue = response.headers.get(headerName);
      if (headerValue) {
        responseHeaders.set(headerName, headerValue);
      }
    }

    // Return the proxied response
    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Proxy request failed:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend service' },
      { status: 502 }
    );
  }
}

// Export handlers for each HTTP method
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params);
}

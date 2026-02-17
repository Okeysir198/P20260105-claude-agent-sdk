/**
 * API Proxy Route
 *
 * Proxies requests to the backend API, adding the API key server-side.
 * This hides the API key from the browser.
 *
 * Usage: /api/proxy/sessions → Backend /api/v1/sessions
 */
import { NextRequest, NextResponse } from 'next/server';
import { resolveSessionToken } from '@/lib/server-auth';

// Server-only environment variables (not prefixed with NEXT_PUBLIC_)
const API_KEY = process.env.API_KEY;
const BACKEND_API_URL = process.env.BACKEND_API_URL;

// Methods that may carry a request body
const BODY_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

// Headers to forward from the client request to the backend
const REQUEST_HEADERS_TO_FORWARD = [
  'content-type',
  'accept',
  'accept-language',
  'cache-control',
  'pragma',
];

// Headers to forward from the backend response to the client
const RESPONSE_HEADERS_TO_FORWARD = [
  'content-type',
  'content-disposition',
  'content-length',
  'cache-control',
  'etag',
  'last-modified',
];

/**
 * Forward a request to the backend with API key authentication.
 * Streams both request and response bodies to avoid buffering and
 * to preserve binary data (multipart uploads, file downloads).
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
  const targetPath = params.path.join('/');
  const searchParams = request.nextUrl.searchParams.toString();
  const queryString = searchParams ? `?${searchParams}` : '';
  const targetUrl = `${BACKEND_API_URL}/${targetPath}${queryString}`;

  // Build headers, forwarding relevant ones from the original request
  const headers = new Headers();

  for (const headerName of REQUEST_HEADERS_TO_FORWARD) {
    const headerValue = request.headers.get(headerName);
    if (headerValue) {
      headers.set(headerName, headerValue);
    }
  }

  // Add the API key header (this is the main purpose of the proxy)
  headers.set('X-API-Key', API_KEY);

  // Add user token header if session exists and is valid
  const sessionToken = await resolveSessionToken(API_KEY);
  if (sessionToken) {
    headers.set('X-User-Token', sessionToken);
  }

  const fetchOptions: RequestInit = {
    method: request.method,
    headers,
  };

  if (BODY_METHODS.has(request.method)) {
    try {
      const buf = await request.arrayBuffer();
      if (buf.byteLength > 0) {
        fetchOptions.body = Buffer.from(buf);
      }
    } catch {
      // No body or error reading body
    }
  }

  try {
    const response = await fetch(targetUrl, fetchOptions);

    // Build response headers to forward back to client
    const responseHeaders = new Headers();

    for (const headerName of RESPONSE_HEADERS_TO_FORWARD) {
      const headerValue = response.headers.get(headerName);
      if (headerValue) {
        responseHeaders.set(headerName, headerValue);
      }
    }

    // Stream the response body through — avoids buffering large file downloads
    return new NextResponse(response.body, {
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

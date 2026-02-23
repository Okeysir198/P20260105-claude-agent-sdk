import { NextRequest, NextResponse } from 'next/server';
import { resolveSessionToken } from '@/lib/server-auth';

const API_KEY = process.env.API_KEY;
const BACKEND_API_URL = process.env.BACKEND_API_URL;

const BODY_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

const REQUEST_HEADERS_TO_FORWARD = [
  'content-type',
  'accept',
  'accept-language',
  'cache-control',
  'pragma',
];

const RESPONSE_HEADERS_TO_FORWARD = [
  'content-type',
  'content-disposition',
  'content-length',
  'cache-control',
  'etag',
  'last-modified',
];

async function proxyRequest(
  request: NextRequest,
  params: { path: string[] }
): Promise<NextResponse> {
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

  const targetPath = params.path.join('/');
  const searchParams = request.nextUrl.searchParams.toString();
  const queryString = searchParams ? `?${searchParams}` : '';
  const targetUrl = `${BACKEND_API_URL}/${targetPath}${queryString}`;

  const headers = new Headers();

  for (const headerName of REQUEST_HEADERS_TO_FORWARD) {
    const headerValue = request.headers.get(headerName);
    if (headerValue) {
      headers.set(headerName, headerValue);
    }
  }

  headers.set('X-API-Key', API_KEY);

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
        fetchOptions.body = new Uint8Array(buf);
      }
    } catch {
      // no body
    }
  }

  try {
    const response = await fetch(targetUrl, fetchOptions);

    const responseHeaders = new Headers();

    for (const headerName of RESPONSE_HEADERS_TO_FORWARD) {
      const headerValue = response.headers.get(headerName);
      if (headerValue) {
        responseHeaders.set(headerName, headerValue);
      }
    }

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

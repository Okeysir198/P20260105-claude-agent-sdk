import { NextRequest } from 'next/server';
import { proxyToBackend } from '@/lib/api-proxy';

export async function GET() {
  return proxyToBackend({
    method: 'GET',
    path: '/api/v1/sessions',
    errorMessage: 'Failed to fetch sessions'
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return proxyToBackend({
    method: 'POST',
    path: '/api/v1/sessions',
    body,
    errorMessage: 'Failed to create session',
    successStatus: 201
  });
}

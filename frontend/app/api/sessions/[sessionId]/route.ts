import { NextRequest } from 'next/server';
import { proxyToBackend } from '@/lib/api-proxy';

interface RouteParams {
  params: Promise<{ sessionId: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { sessionId } = await params;
  return proxyToBackend({
    method: 'GET',
    path: `/api/v1/sessions/${sessionId}`,
    errorMessage: 'Failed to fetch session'
  });
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  const { sessionId } = await params;
  return proxyToBackend({
    method: 'DELETE',
    path: `/api/v1/sessions/${sessionId}`,
    errorMessage: 'Failed to delete session',
    successStatus: 204
  });
}

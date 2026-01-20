import { NextRequest } from 'next/server';
import { proxyToBackend } from '@/lib/api-proxy';

interface RouteParams {
  params: Promise<{ sessionId: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const { sessionId } = await params;
  return proxyToBackend({
    method: 'POST',
    path: `/api/v1/conversations/${sessionId}/interrupt`,
    errorMessage: 'Failed to interrupt conversation'
  });
}

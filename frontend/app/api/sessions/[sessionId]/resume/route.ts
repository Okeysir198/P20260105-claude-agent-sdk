import { NextRequest } from 'next/server';
import { proxyToBackend } from '@/lib/api-proxy';

interface RouteParams {
  params: Promise<{ sessionId: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const { sessionId } = await params;
  // Backend expects resume_session_id in the request body at POST /api/v1/sessions/resume
  return proxyToBackend({
    method: 'POST',
    path: '/api/v1/sessions/resume',
    body: { resume_session_id: sessionId },
    errorMessage: 'Failed to resume session'
  });
}

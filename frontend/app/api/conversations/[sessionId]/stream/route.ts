import { NextRequest } from 'next/server';

export const runtime = 'edge';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:7001';

interface RouteParams {
  params: Promise<{ sessionId: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const { sessionId } = await params;
  const body = await request.json();

  const response = await fetch(
    `${BACKEND_URL}/api/v1/conversations/${sessionId}/stream`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }
  );

  if (!response.ok && !response.body) {
    return new Response(
      JSON.stringify({ error: 'Failed to stream message' }),
      {
        status: response.status,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  // Create a TransformStream to avoid buffering
  const { readable, writable } = new TransformStream();

  // Pipe the backend response through the transform stream
  response.body?.pipeTo(writable).catch((error) => {
    console.error('Error piping stream:', error);
  });

  // Return the transformed stream with SSE headers
  return new Response(readable, {
    status: response.status,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no', // Disable nginx buffering
    },
  });
}

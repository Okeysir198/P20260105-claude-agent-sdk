import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:19830';

interface RouteParams {
  params: Promise<{ sessionId: string }>;
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
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
      return NextResponse.json(
        { error: 'Failed to stream message' },
        { status: response.status }
      );
    }

    // Forward SSE stream
    return new Response(response.body, {
      status: response.status,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Error streaming message:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from 'next/server';
import { resolveSessionToken } from '@/lib/server-auth';

const API_KEY = process.env.API_KEY;
const BACKEND_API_URL = process.env.BACKEND_API_URL;

export async function POST(request: NextRequest) {
  if (!API_KEY || !BACKEND_API_URL) {
    return NextResponse.json(
      { error: 'Server configuration error' },
      { status: 500 }
    );
  }

  const sessionToken = await resolveSessionToken(API_KEY);
  if (!sessionToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Parse incoming multipart form data
  let incomingForm: FormData;
  try {
    incomingForm = await request.formData();
  } catch {
    return NextResponse.json({ error: 'Invalid form data' }, { status: 400 });
  }

  const file = incomingForm.get('file') as File | null;
  const sessionId = incomingForm.get('session_id') as string | null;

  if (!file || !sessionId) {
    return NextResponse.json(
      { error: 'Both "file" and "session_id" fields are required' },
      { status: 400 }
    );
  }

  // Build new FormData for backend
  const backendForm = new FormData();
  backendForm.append('file', file, file.name);
  backendForm.append('session_id', sessionId);

  try {
    const response = await fetch(`${BACKEND_API_URL}/files/upload`, {
      method: 'POST',
      headers: {
        'X-API-Key': API_KEY,
        'X-User-Token': sessionToken,
      },
      body: backendForm,
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('File upload proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to upload file to backend' },
      { status: 502 }
    );
  }
}

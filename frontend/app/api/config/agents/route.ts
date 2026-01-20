import { proxyToBackend } from '@/lib/api-proxy';

export async function GET() {
  return proxyToBackend({
    method: 'GET',
    path: '/api/v1/config/agents',
    errorMessage: 'Failed to fetch agents'
  });
}

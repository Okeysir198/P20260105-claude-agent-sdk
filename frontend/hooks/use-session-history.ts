import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { QUERY_KEYS } from '@/lib/constants';

export function useSessionHistory(sessionId: string | null) {
  return useQuery({
    queryKey: [QUERY_KEYS.SESSION_HISTORY, sessionId],
    queryFn: () => apiClient.getSessionHistory(sessionId!),
    enabled: !!sessionId,
    staleTime: 0, // Always refetch history when loading a session
  });
}

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { QUERY_KEYS } from '@/lib/constants';

export function useAgents() {
  return useQuery({
    queryKey: [QUERY_KEYS.AGENTS],
    queryFn: () => apiClient.getAgents(),
    staleTime: Infinity, // Agents don't change frequently
  });
}

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { QUERY_KEYS } from '@/lib/constants';
import type { SearchResponse } from '@/types/api';

interface UseSessionSearchOptions {
  enabled?: boolean;
  maxResults?: number;
}

export function useSessionSearch(
  query: string,
  options: UseSessionSearchOptions = {}
) {
  const { enabled = true, maxResults = 20 } = options;

  return useQuery<SearchResponse>({
    queryKey: [QUERY_KEYS.SESSION_SEARCH, query],
    queryFn: () => apiClient.searchSessions(query, maxResults),
    enabled: enabled && query.trim().length > 0,
    staleTime: 30000, // 30 seconds - search results stay fresh for a while
    gcTime: 60000, // 1 minute - keep in cache longer
    retry: 1,
  });
}

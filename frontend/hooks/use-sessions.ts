import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { QUERY_KEYS } from '@/lib/constants';
import { toast } from 'sonner';

export function useSessions() {
  return useQuery({
    queryKey: [QUERY_KEYS.SESSIONS],
    queryFn: () => apiClient.getSessions(),
    refetchOnWindowFocus: true,
    retry: 1,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentId?: string) => apiClient.createSession(agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
      toast.success('New conversation created');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create conversation');
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.deleteSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
      toast.success('Conversation deleted');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete conversation');
    },
  });
}

export function useCloseSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.closeSession(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to close conversation');
    },
  });
}

export function useResumeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, initialMessage }: { id: string; initialMessage?: string }) =>
      apiClient.resumeSession(id, initialMessage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to resume conversation');
    },
  });
}

export function useUpdateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string | null }) =>
      apiClient.updateSession(id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update conversation');
    },
  });
}

export function useBatchDeleteSessions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionIds: string[]) => apiClient.batchDeleteSessions(sessionIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
      toast.success('Conversations deleted');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete conversations');
    },
  });
}

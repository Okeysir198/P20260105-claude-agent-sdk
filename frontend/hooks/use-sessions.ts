'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import type { SessionInfo, SessionListResponse } from '@/types/sessions';
import { DEFAULT_API_URL } from '@/lib/constants';

/**
 * Options for configuring the useSessions hook behavior.
 */
interface UseSessionsOptions {
  /** Base URL for the API. Defaults to DEFAULT_API_URL from constants. */
  apiBaseUrl?: string;
  /** Whether to automatically refresh sessions periodically. Defaults to false. */
  autoRefresh?: boolean;
  /** Interval in milliseconds for auto-refresh. Defaults to 30000 (30 seconds). */
  refreshInterval?: number;
  /** Whether to fetch sessions immediately on mount. Defaults to true. */
  fetchOnMount?: boolean;
}

/**
 * Return type for the useSessions hook.
 */
interface UseSessionsReturn {
  /** Combined array of all sessions (active + history). */
  sessions: SessionInfo[];
  /** Array of active session IDs. */
  activeSessions: string[];
  /** Array of history session IDs. */
  historySessions: string[];
  /** Raw active sessions data from the API. */
  activeSessionsData: SessionInfo[];
  /** Raw history sessions data from the API. */
  historySessionsData: SessionInfo[];
  /** Whether sessions are currently being fetched. */
  isLoading: boolean;
  /** Error message if the last operation failed, null otherwise. */
  error: string | null;
  /** Manually refresh the sessions list. */
  refresh: () => Promise<void>;
  /** Resume an existing session by its ID. */
  resumeSession: (sessionId: string, initialMessage?: string) => Promise<SessionInfo>;
  /** Delete a session by its ID (if supported by the API). */
  deleteSession: (sessionId: string) => Promise<void>;
  /** Session totals from the API response. */
  totals: { active: number; history: number; total: number };
}

/**
 * Hook for managing session history with the Claude Chat API.
 *
 * @param options - Configuration options for the hook
 * @returns Session data and management functions
 *
 * @example
 * ```tsx
 * const {
 *   sessions,
 *   activeSessions,
 *   isLoading,
 *   error,
 *   refresh,
 *   resumeSession
 * } = useSessions({
 *   autoRefresh: true,
 *   refreshInterval: 60000
 * });
 * ```
 */
export function useSessions(options: UseSessionsOptions = {}): UseSessionsReturn {
  const {
    apiBaseUrl = DEFAULT_API_URL,
    autoRefresh = false,
    refreshInterval = 30000,
    fetchOnMount = true,
  } = options;

  // State for sessions data
  const [activeSessionsData, setActiveSessionsData] = useState<SessionInfo[]>([]);
  const [historySessionsData, setHistorySessionsData] = useState<SessionInfo[]>([]);
  const [totals, setTotals] = useState<{ active: number; history: number; total: number }>({
    active: 0,
    history: 0,
    total: 0,
  });

  // Loading and error states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ref to track if component is mounted (for cleanup)
  const isMountedRef = useRef(true);
  // Ref to store the interval ID for cleanup
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Convert a session ID string to a SessionInfo object.
   */
  const sessionIdToInfo = (sessionId: string, isActive: boolean): SessionInfo => ({
    id: sessionId,
    created_at: new Date().toISOString(),
    last_activity: new Date().toISOString(),
    turn_count: 0,
  });

  /**
   * Fetch sessions from the API.
   */
  const fetchSessions = useCallback(async (): Promise<void> => {
    if (!isMountedRef.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/sessions`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.error || `Failed to fetch sessions: ${response.status} ${response.statusText}`
        );
      }

      // Backend returns { active_sessions: string[], history_sessions: string[], total_active, total_history }
      const data = await response.json();

      if (isMountedRef.current) {
        // Convert string arrays to SessionInfo arrays
        const activeIds: string[] = data.active_sessions || [];
        const historyIds: string[] = data.history_sessions || [];

        setActiveSessionsData(activeIds.map((id: string) => sessionIdToInfo(id, true)));
        setHistorySessionsData(historyIds.map((id: string) => sessionIdToInfo(id, false)));
        setTotals({
          active: data.total_active || activeIds.length,
          history: data.total_history || historyIds.length,
          total: (data.total_active || activeIds.length) + (data.total_history || historyIds.length),
        });
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
        setError(errorMessage);
        console.error('Failed to fetch sessions:', err);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [apiBaseUrl]);

  /**
   * Resume an existing session by ID.
   *
   * @param sessionId - The ID of the session to resume
   * @param initialMessage - Optional message to send when resuming
   * @returns The resumed session info
   */
  const resumeSession = useCallback(
    async (sessionId: string, initialMessage?: string): Promise<SessionInfo> => {
      setError(null);

      try {
        const response = await fetch(`${apiBaseUrl}/sessions/${sessionId}/resume`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: sessionId,
            initial_message: initialMessage,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.error || `Failed to resume session: ${response.status} ${response.statusText}`
          );
        }

        const data = await response.json();

        // Refresh sessions list after successful resume
        if (isMountedRef.current) {
          await fetchSessions();
        }

        return data;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to resume session';
        if (isMountedRef.current) {
          setError(errorMessage);
        }
        throw new Error(errorMessage);
      }
    },
    [apiBaseUrl, fetchSessions]
  );

  /**
   * Delete a session by ID.
   *
   * @param sessionId - The ID of the session to delete
   */
  const deleteSession = useCallback(
    async (sessionId: string): Promise<void> => {
      setError(null);

      try {
        const response = await fetch(`${apiBaseUrl}/sessions/${sessionId}`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.error || `Failed to delete session: ${response.status} ${response.statusText}`
          );
        }

        // Remove the deleted session from local state immediately
        if (isMountedRef.current) {
          setActiveSessionsData((prev) => prev.filter((s) => s.id !== sessionId));
          setHistorySessionsData((prev) => prev.filter((s) => s.id !== sessionId));
          setTotals((prev) => ({
            ...prev,
            total: Math.max(0, prev.total - 1),
          }));
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to delete session';
        if (isMountedRef.current) {
          setError(errorMessage);
        }
        throw new Error(errorMessage);
      }
    },
    [apiBaseUrl]
  );

  /**
   * Public refresh function that can be called externally.
   */
  const refresh = useCallback(async (): Promise<void> => {
    await fetchSessions();
  }, [fetchSessions]);

  // Initial fetch on mount
  useEffect(() => {
    isMountedRef.current = true;

    if (fetchOnMount) {
      fetchSessions();
    }

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchOnMount, fetchSessions]);

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(() => {
        fetchSessions();
      }, refreshInterval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, refreshInterval, fetchSessions]);

  // Derived values
  const sessions: SessionInfo[] = [...activeSessionsData, ...historySessionsData];
  const activeSessions: string[] = activeSessionsData.map((s) => s.id);
  const historySessions: string[] = historySessionsData.map((s) => s.id);

  return {
    sessions,
    activeSessions,
    historySessions,
    activeSessionsData,
    historySessionsData,
    isLoading,
    error,
    refresh,
    resumeSession,
    deleteSession,
    totals,
  };
}

export default useSessions;

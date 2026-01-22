'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import type { SessionInfo } from '@/types/sessions';
import { apiRequest, getApiErrorMessage } from '@/lib/api-client';
import { getErrorMessage } from './use-claude-chat';

/**
 * Options for configuring the useSessions hook behavior.
 */
interface UseSessionsOptions {
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
  sessions: SessionInfo[];
  activeSessions: string[];
  historySessions: string[];
  activeSessionsData: SessionInfo[];
  historySessionsData: SessionInfo[];
  pinnedSessions: SessionInfo[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  resumeSession: (sessionId: string, initialMessage?: string) => Promise<SessionInfo>;
  deleteSession: (sessionId: string) => Promise<void>;
  togglePin: (sessionId: string) => Promise<void>;
  exportSession: (sessionId: string, format: 'markdown' | 'json') => Promise<void>;
  totals: { active: number; history: number; total: number };
}

/**
 * API session item with first_message
 */
interface APISessionItem {
  session_id: string;
  first_message?: string | null;
  created_at?: string;
  turn_count?: number;
  is_active?: boolean;
}

/**
 * Convert an API session item to SessionInfo.
 */
function apiSessionToInfo(session: APISessionItem): SessionInfo {
  return {
    id: session.session_id,
    created_at: session.created_at || new Date().toISOString(),
    last_activity: session.created_at || new Date().toISOString(),
    turn_count: session.turn_count || 0,
    preview: session.first_message || undefined,
  };
}

/**
 * Convert a session ID string to a SessionInfo object (fallback).
 */
function sessionIdToInfo(sessionId: string): SessionInfo {
  return {
    id: sessionId,
    created_at: new Date().toISOString(),
    last_activity: new Date().toISOString(),
    turn_count: 0,
  };
}

/**
 * Hook for managing session history with the Claude Chat API.
 */
export function useSessions(options: UseSessionsOptions = {}): UseSessionsReturn {
  const {
    autoRefresh = false,
    refreshInterval = 30000,
    fetchOnMount = true,
  } = options;

  // State for sessions data
  const [activeSessionsData, setActiveSessionsData] = useState<SessionInfo[]>([]);
  const [historySessionsData, setHistorySessionsData] = useState<SessionInfo[]>([]);
  const [pinnedSessions, setPinnedSessions] = useState<SessionInfo[]>([]);
  const [totals, setTotals] = useState({ active: 0, history: 0, total: 0 });

  // Loading and error states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load pinned sessions from localStorage
  const loadPinnedSessions = useCallback(() => {
    try {
      const pinned = localStorage.getItem('pinned_sessions');
      return pinned ? JSON.parse(pinned) : [];
    } catch {
      return [];
    }
  }, []);

  // Save pinned sessions to localStorage
  const savePinnedSessions = useCallback((sessionIds: string[]) => {
    try {
      localStorage.setItem('pinned_sessions', JSON.stringify(sessionIds));
    } catch (error) {
      console.error('Failed to save pinned sessions:', error);
    }
  }, []);

  // Ref to track if component is mounted
  const isMountedRef = useRef(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Fetch sessions from the API.
   */
  const fetchSessions = useCallback(async (): Promise<void> => {
    if (!isMountedRef.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiRequest('/sessions');

      if (!response.ok) {
        const errorMessage = await getApiErrorMessage(response, 'Failed to fetch sessions');
        throw new Error(errorMessage);
      }

      const data = await response.json();

      if (!isMountedRef.current) return;

      const activeIds: string[] = data.active_sessions || [];
      const historyIds: string[] = data.history_sessions || [];
      const sessionsData: APISessionItem[] = data.sessions || [];

      // Create a map of session data by ID for quick lookup
      const sessionMap = new Map<string, APISessionItem>();
      for (const session of sessionsData) {
        sessionMap.set(session.session_id, session);
      }

      // Map session IDs to full SessionInfo objects
      const mapIdToSession = (id: string): SessionInfo => {
        const sessionData = sessionMap.get(id);
        return sessionData ? apiSessionToInfo(sessionData) : sessionIdToInfo(id);
      };

      // Filter sessions into active and history based on the ordered lists
      const activeSet = new Set(activeIds);
      const historyFiltered = historyIds.filter(id => !activeSet.has(id));

      const activeData = activeIds.filter(id => sessionMap.has(id)).map(mapIdToSession);
      const historyData = historyFiltered.map(mapIdToSession);

      setActiveSessionsData(activeData);
      setHistorySessionsData(historyData);

      // Update pinned sessions with current data
      const pinnedIds = loadPinnedSessions();
      const allSessions = [...activeData, ...historyData];
      const pinned = allSessions.filter(s => pinnedIds.includes(s.id));
      setPinnedSessions(pinned);

      setTotals({
        active: data.total_active || activeIds.length,
        history: data.total_history || historyIds.length,
        total: (data.total_active || activeIds.length) + (data.total_history || historyIds.length),
      });
    } catch (err) {
      if (!isMountedRef.current) return;
      setError(getErrorMessage(err));
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  /**
   * Resume an existing session by ID.
   */
  const resumeSession = useCallback(
    async (sessionId: string, initialMessage?: string): Promise<SessionInfo> => {
      setError(null);

      const response = await apiRequest(`/sessions/${sessionId}/resume`, {
        method: 'POST',
        body: {
          session_id: sessionId,
          initial_message: initialMessage,
        },
      });

      if (!response.ok) {
        const errorMessage = await getApiErrorMessage(response, 'Failed to resume session');
        if (isMountedRef.current) setError(errorMessage);
        throw new Error(errorMessage);
      }

      const data = await response.json();

      if (isMountedRef.current) {
        await fetchSessions();
      }

      return data;
    },
    [fetchSessions]
  );

  /**
   * Delete a session by ID.
   */
  const deleteSession = useCallback(
    async (sessionId: string): Promise<void> => {
      setError(null);

      const response = await apiRequest(`/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorMessage = await getApiErrorMessage(response, 'Failed to delete session');
        if (isMountedRef.current) setError(errorMessage);
        throw new Error(errorMessage);
      }

      if (!isMountedRef.current) return;

      // Optimistically remove from local state
      setActiveSessionsData((prev) => prev.filter((s) => s.id !== sessionId));
      setHistorySessionsData((prev) => prev.filter((s) => s.id !== sessionId));
      setPinnedSessions((prev) => prev.filter((s) => s.id !== sessionId));
      setTotals((prev) => ({
        ...prev,
        total: Math.max(0, prev.total - 1),
      }));

      // Remove from pinned IDs
      const pinnedIds = loadPinnedSessions().filter((id: string) => id !== sessionId);
      savePinnedSessions(pinnedIds);
    },
    [loadPinnedSessions, savePinnedSessions]
  );

  /**
   * Toggle pin status for a session.
   */
  const togglePin = useCallback(
    async (sessionId: string): Promise<void> => {
      const pinnedIds = loadPinnedSessions();
      const isPinned = pinnedIds.includes(sessionId);

      if (isPinned) {
        const newPinnedIds = pinnedIds.filter((id: string) => id !== sessionId);
        savePinnedSessions(newPinnedIds);
        setPinnedSessions((prev) => prev.filter((s) => s.id !== sessionId));
      } else {
        const newPinnedIds = [...pinnedIds, sessionId];
        savePinnedSessions(newPinnedIds);

        // Find and add to pinned sessions
        const allSessions = [...activeSessionsData, ...historySessionsData];
        const session = allSessions.find((s) => s.id === sessionId);
        if (session) {
          setPinnedSessions((prev) => [...prev, { ...session, is_pinned: true }]);
        }
      }
    },
    [activeSessionsData, historySessionsData, loadPinnedSessions, savePinnedSessions]
  );

  /**
   * Export session history.
   */
  const exportSession = useCallback(
    async (sessionId: string, format: 'markdown' | 'json'): Promise<void> => {
      try {
        const response = await apiRequest(`/sessions/${sessionId}/history`);

        if (!response.ok) {
          throw new Error('Failed to fetch session history');
        }

        const data = await response.json();
        const messages = data.messages || [];

        if (format === 'json') {
          const content = JSON.stringify({ session_id: sessionId, messages }, null, 2);
          const blob = new Blob([content], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `session-${sessionId.slice(0, 8)}.json`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        } else {
          const lines: string[] = [`# Session ${sessionId}`, '', '---', ''];
          for (const msg of messages) {
            const role = msg.role === 'assistant' ? 'Claude' : 'User';
            lines.push(`### ${role}`, '', msg.content, '', '---', '');
          }
          const content = lines.join('\n');
          const blob = new Blob([content], { type: 'text/markdown' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `session-${sessionId.slice(0, 8)}.md`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to export session';
        if (isMountedRef.current) setError(errorMessage);
        throw error;
      }
    },
    []
  );

  /**
   * Public refresh function.
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
      intervalRef.current = setInterval(fetchSessions, refreshInterval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, refreshInterval, fetchSessions]);

  // Memoized derived values
  const sessions = useMemo(
    () => [...activeSessionsData, ...historySessionsData],
    [activeSessionsData, historySessionsData]
  );

  const activeSessions = useMemo(
    () => activeSessionsData.map((s) => s.id),
    [activeSessionsData]
  );

  const historySessions = useMemo(
    () => historySessionsData.map((s) => s.id),
    [historySessionsData]
  );

  return {
    sessions,
    activeSessions,
    historySessions,
    activeSessionsData,
    historySessionsData,
    pinnedSessions,
    isLoading,
    error,
    refresh,
    resumeSession,
    deleteSession,
    togglePin,
    exportSession,
    totals,
  };
}

export default useSessions;

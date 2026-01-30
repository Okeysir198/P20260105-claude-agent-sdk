import { useRef, useState, useCallback, useEffect } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { apiClient } from '@/lib/api-client';
import { convertHistoryToChatMessages } from '@/lib/history-utils';
import type { ChatMessage } from '@/types';

const MAX_HISTORY_RETRIES = 3;

interface HistoryLoadingState {
  hasLoadedHistory: React.MutableRefObject<boolean>;
  historyError: string | null;
  historyRetryCount: number;
  isLoadingHistory: boolean;
  handleHistoryRetry: () => void;
}

export function useHistoryLoading(): HistoryLoadingState {
  const sessionId = useChatStore((s) => s.sessionId);
  const messages = useChatStore((s) => s.messages);
  const setMessages = useChatStore((s) => s.setMessages);

  const hasLoadedHistory = useRef(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyRetryCount, setHistoryRetryCount] = useState(0);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const loadHistory = useCallback(async () => {
    if (!sessionId || isLoadingHistory) return;

    setIsLoadingHistory(true);
    setHistoryError(null);

    try {
      const historyData = await apiClient.getSessionHistory(sessionId);
      const chatMessages = convertHistoryToChatMessages(historyData.messages);

      if (chatMessages.length > 0) {
        setMessages(chatMessages);
      }
      hasLoadedHistory.current = true;
      setHistoryRetryCount(0);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to load session history:', error);
      setHistoryError(errorMessage);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [sessionId, isLoadingHistory, setMessages]);

  const handleHistoryRetry = useCallback(() => {
    if (historyRetryCount < MAX_HISTORY_RETRIES) {
      setHistoryRetryCount((prev) => prev + 1);
      loadHistory();
    }
  }, [historyRetryCount, loadHistory]);

  // Reset history loaded flag when session changes
  useEffect(() => {
    // Only reset if there are no messages (messages may have been loaded by SessionItem)
    if (messages.length === 0) {
      hasLoadedHistory.current = false;
    }
    setHistoryError(null);
    setHistoryRetryCount(0);
  }, [sessionId, messages.length]);

  // Load session history on mount when there's a sessionId but no messages
  useEffect(() => {
    if (sessionId && !hasLoadedHistory.current && messages.length === 0) {
      loadHistory();
    }
  }, [sessionId, messages.length, loadHistory]);

  return {
    hasLoadedHistory,
    historyError,
    historyRetryCount,
    isLoadingHistory,
    handleHistoryRetry,
  };
}

'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import type { Message, SessionHistoryResponse } from '@/types/messages';
import {
  createUserMessage,
  createAssistantMessage,
  createToolUseMessage,
  createToolResultMessage,
  createMessageId,
  convertHistoryToMessages,
} from '@/types/messages';
import type { WebSocketEvent } from '@/types/events';
import { API_KEY, DEFAULT_WS_URL } from '@/lib/constants';
import { apiRequest } from '@/lib/api-client';
import { useWebSocket, ConnectionState } from './use-websocket';

/**
 * Options for configuring the useClaudeChat hook
 */
interface UseClaudeChatOptions {
  /** Base URL for WebSocket. Defaults to DEFAULT_WS_URL */
  wsBaseUrl?: string;
  /** Agent ID to use for the conversation */
  agentId?: string;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
  /** Callback when a new session is created */
  onSessionCreated?: (sessionId: string) => void;
  /** Callback when a conversation turn completes */
  onDone?: (turnCount: number, cost?: number) => void;
}

/**
 * Return type for the useClaudeChat hook
 */
interface UseClaudeChatReturn {
  // State
  messages: Message[];
  sessionId: string | null;
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
  turnCount: number;
  totalCostUsd: number | undefined;
  connectionState: ConnectionState;

  // Actions
  sendMessage: (content: string) => Promise<void>;
  interrupt: () => Promise<void>;
  clearMessages: () => void;
  resumeSession: (sessionId: string) => Promise<void>;
  startNewSession: () => void;
}

/**
 * Extract error message from various error types
 */
export function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return 'An unknown error occurred';
}

/**
 * Main hook for managing Claude chat conversations with WebSocket streaming.
 */
export function useClaudeChat(options: UseClaudeChatOptions = {}): UseClaudeChatReturn {
  const {
    wsBaseUrl = DEFAULT_WS_URL,
    agentId,
    onError,
    onSessionCreated,
    onDone,
  } = options;

  // Conversation state
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [turnCount, setTurnCount] = useState(0);
  const [totalCostUsd, setTotalCostUsd] = useState<number | undefined>(undefined);

  // Refs for managing streaming state
  const currentAssistantMessageId = useRef<string | null>(null);
  const accumulatedText = useRef<string>('');
  const pendingMessage = useRef<string | null>(null);

  /**
   * Update the current assistant message with accumulated text
   */
  const updateAssistantMessage = useCallback((text: string, isComplete: boolean = false): void => {
    const messageId = currentAssistantMessageId.current;
    if (!messageId) return;

    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId && msg.role === 'assistant'
          ? { ...msg, content: text, isStreaming: !isComplete }
          : msg
      )
    );
  }, []);

  /**
   * Reset streaming state
   */
  const resetStreamingState = useCallback((): void => {
    setIsStreaming(false);
    setIsLoading(false);
    currentAssistantMessageId.current = null;
    accumulatedText.current = '';
  }, []);

  /**
   * Handle error and update state
   */
  const handleError = useCallback((errorMessage: string): void => {
    setError(errorMessage);
    onError?.(errorMessage);
    resetStreamingState();
  }, [onError, resetStreamingState]);

  /**
   * Handle individual WebSocket events
   */
  const handleWebSocketEvent = useCallback((event: WebSocketEvent): void => {
    switch (event.type) {
      case 'ready': {
        // Connection is ready - handled by useWebSocket isReady flag
        break;
      }

      case 'session_id': {
        const newSessionId = event.session_id;
        setSessionId(newSessionId);
        onSessionCreated?.(newSessionId);
        break;
      }

      case 'text_delta': {
        accumulatedText.current += event.text;
        updateAssistantMessage(accumulatedText.current);
        break;
      }

      case 'tool_use': {
        // Finalize any current assistant message before tool use
        if (accumulatedText.current && currentAssistantMessageId.current) {
          updateAssistantMessage(accumulatedText.current, true);
        }

        const toolUseMessage = createToolUseMessage(
          event.name,
          event.input,
          createMessageId()
        );
        setMessages((prev) => [...prev, toolUseMessage]);
        break;
      }

      case 'tool_result': {
        const toolResultMessage = createToolResultMessage(
          event.tool_use_id,
          event.content,
          event.is_error
        );
        setMessages((prev) => [...prev, toolResultMessage]);

        // Create new assistant message for continued response
        accumulatedText.current = '';
        const newAssistantMessage = createAssistantMessage('', true);
        currentAssistantMessageId.current = newAssistantMessage.id;
        setMessages((prev) => [...prev, newAssistantMessage]);
        break;
      }

      case 'done': {
        if (currentAssistantMessageId.current) {
          updateAssistantMessage(accumulatedText.current, true);
        }

        // Remove empty assistant message when stream finishes
        if (!accumulatedText.current) {
          setMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage?.role === 'assistant' && !lastMessage.content) {
              return prev.slice(0, -1);
            }
            return prev;
          });
        }

        setTurnCount(event.turn_count);
        if (event.total_cost_usd !== undefined) {
          setTotalCostUsd(event.total_cost_usd);
        }

        onDone?.(event.turn_count, event.total_cost_usd);
        resetStreamingState();
        // Note: We do NOT disconnect here - keep connection open for follow-ups
        break;
      }

      case 'error': {
        handleError(event.error);
        break;
      }
    }
  }, [updateAssistantMessage, resetStreamingState, handleError, onSessionCreated, onDone]);

  // WebSocket hook
  const { state: connectionState, connect, disconnect, send, isReady } = useWebSocket({
    onMessage: handleWebSocketEvent,
    onError: (err) => handleError(err.message),
  });

  // Send pending message when WebSocket becomes ready
  useEffect(() => {
    if (isReady && pendingMessage.current) {
      const content = pendingMessage.current;
      pendingMessage.current = null;
      send({ content });
    }
  }, [isReady, send]);

  /**
   * Remove empty trailing assistant message
   */
  const removeEmptyAssistantMessage = useCallback((): void => {
    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (lastMessage?.role === 'assistant' && !lastMessage.content) {
        return prev.slice(0, -1);
      }
      return prev;
    });
  }, []);

  /**
   * Send a message to the Claude API via WebSocket
   */
  const sendMessage = useCallback(async (content: string): Promise<void> => {
    if (!content.trim() || isLoading) return;

    setError(null);
    setIsLoading(true);
    setIsStreaming(true);

    // Add user message
    const userMessage = createUserMessage(content);
    setMessages((prev) => [...prev, userMessage]);

    // Create assistant message placeholder
    accumulatedText.current = '';
    const assistantMessage = createAssistantMessage('', true);
    currentAssistantMessageId.current = assistantMessage.id;
    setMessages((prev) => [...prev, assistantMessage]);

    // If WebSocket is ready, send immediately
    if (isReady) {
      const success = send({ content });
      if (!success) {
        handleError('Failed to send message');
        removeEmptyAssistantMessage();
      }
      return;
    }

    // If not connected, connect and queue the message
    if (connectionState === 'disconnected' || connectionState === 'error') {
      pendingMessage.current = content;
      // Build WebSocket URL with API key and optional agent ID
      const params = new URLSearchParams();
      if (API_KEY) {
        params.set('api_key', API_KEY);
      }
      if (agentId) {
        params.set('agent_id', agentId);
      }
      const queryString = params.toString();
      const url = queryString ? `${wsBaseUrl}?${queryString}` : wsBaseUrl;
      connect(url);
      return;
    }

    // If connecting, just queue the message
    if (connectionState === 'connecting') {
      pendingMessage.current = content;
      return;
    }

    // Connected but not ready yet - queue the message
    pendingMessage.current = content;
  }, [isLoading, isReady, connectionState, agentId, wsBaseUrl, connect, send, handleError, removeEmptyAssistantMessage]);

  /**
   * Interrupt the current streaming response
   */
  const interrupt = useCallback(async (): Promise<void> => {
    // Call interrupt endpoint if we have a session
    if (sessionId) {
      try {
        await apiRequest(`/conversations/${sessionId}/interrupt`, {
          method: 'POST',
        });
      } catch {
        // Ignore interrupt endpoint errors
      }
    }

    // Finalize current message
    if (currentAssistantMessageId.current) {
      setMessages((prev) => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage?.role === 'assistant' && !lastMessage.content) {
          return prev.slice(0, -1);
        }
        return prev.map((msg) =>
          msg.id === currentAssistantMessageId.current && msg.role === 'assistant'
            ? { ...msg, isStreaming: false }
            : msg
        );
      });
    }

    setIsStreaming(false);
    setIsLoading(false);
  }, [sessionId]);

  /**
   * Clear all messages and reset state
   */
  const clearMessages = useCallback((): void => {
    disconnect();

    setMessages([]);
    setSessionId(null);
    setError(null);
    setTurnCount(0);
    setTotalCostUsd(undefined);
    setIsLoading(false);
    setIsStreaming(false);
    currentAssistantMessageId.current = null;
    accumulatedText.current = '';
    pendingMessage.current = null;
  }, [disconnect]);

  /**
   * Resume an existing session by loading its history
   */
  const resumeSession = useCallback(async (targetSessionId: string): Promise<void> => {
    // Disconnect any existing WebSocket connection
    disconnect();

    setIsLoading(true);
    setError(null);

    try {
      const historyResponse = await apiRequest(`/sessions/${targetSessionId}/history`);

      if (!historyResponse.ok) {
        if (historyResponse.status === 404) {
          // No history found, start fresh with this session ID
          setSessionId(targetSessionId);
          setMessages([]);
          return;
        }
        throw new Error(`Failed to fetch session history: ${historyResponse.status}`);
      }

      const historyData: SessionHistoryResponse = await historyResponse.json();

      setSessionId(targetSessionId);

      if (historyData.messages && historyData.messages.length > 0) {
        const loadedMessages = convertHistoryToMessages(historyData.messages);
        setMessages(loadedMessages);
        setTurnCount(Math.ceil(loadedMessages.filter((m) => m.role === 'user').length));
      } else {
        setMessages([]);
      }
    } catch (err) {
      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [onError, disconnect]);

  /**
   * Start a fresh new session
   */
  const startNewSession = useCallback((): void => {
    clearMessages();
  }, [clearMessages]);

  return {
    // State
    messages,
    sessionId,
    isLoading,
    isStreaming,
    error,
    turnCount,
    totalCostUsd,
    connectionState,

    // Actions
    sendMessage,
    interrupt,
    clearMessages,
    resumeSession,
    startNewSession,
  };
}

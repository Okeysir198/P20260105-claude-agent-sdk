'use client';

import { useState, useCallback, useRef } from 'react';
import type { Message, SessionHistoryResponse } from '@/types/messages';
import {
  createUserMessage,
  createAssistantMessage,
  createToolUseMessage,
  createToolResultMessage,
  createMessageId,
  convertHistoryToMessages,
} from '@/types/messages';
import type { ParsedSSEEvent } from '@/types/events';
import { DEFAULT_API_URL } from '@/lib/constants';
import { parseSSEStream } from './use-sse-stream';

/**
 * Options for configuring the useClaudeChat hook
 */
interface UseClaudeChatOptions {
  /** Base URL for the API. Defaults to DEFAULT_API_URL */
  apiBaseUrl?: string;
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

  // Actions
  sendMessage: (content: string) => Promise<void>;
  interrupt: () => Promise<void>;
  clearMessages: () => void;
  resumeSession: (sessionId: string) => Promise<void>;
  startNewSession: () => void;

  // Refs
  abortController: React.MutableRefObject<AbortController | null>;
}

/**
 * Extract error message from various error types
 */
function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return 'An unknown error occurred';
}

/**
 * Main hook for managing Claude chat conversations with SSE streaming.
 */
export function useClaudeChat(options: UseClaudeChatOptions = {}): UseClaudeChatReturn {
  const {
    apiBaseUrl = DEFAULT_API_URL,
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
  const abortController = useRef<AbortController | null>(null);
  const currentAssistantMessageId = useRef<string | null>(null);
  const accumulatedText = useRef<string>('');

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
   * Handle individual SSE events
   */
  const handleSSEEvent = useCallback((event: ParsedSSEEvent): void => {
    switch (event.type) {
      case 'session_id': {
        const newSessionId = event.data.session_id;
        setSessionId(newSessionId);
        onSessionCreated?.(newSessionId);
        break;
      }

      case 'text_delta': {
        accumulatedText.current += event.data.text;
        updateAssistantMessage(accumulatedText.current);
        break;
      }

      case 'tool_use': {
        // Finalize any current assistant message before tool use
        if (accumulatedText.current && currentAssistantMessageId.current) {
          updateAssistantMessage(accumulatedText.current, true);
        }

        const toolUseMessage = createToolUseMessage(
          event.data.tool_name,
          event.data.input,
          createMessageId()
        );
        setMessages((prev) => [...prev, toolUseMessage]);
        break;
      }

      case 'tool_result': {
        const toolResultMessage = createToolResultMessage(
          event.data.tool_use_id,
          event.data.content,
          event.data.is_error
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

        setTurnCount(event.data.turn_count);
        if (event.data.total_cost_usd !== undefined) {
          setTotalCostUsd(event.data.total_cost_usd);
        }

        onDone?.(event.data.turn_count, event.data.total_cost_usd);
        resetStreamingState();
        break;
      }

      case 'error': {
        handleError(event.data.error);
        break;
      }
    }
  }, [updateAssistantMessage, resetStreamingState, handleError, onSessionCreated, onDone]);

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
   * Finalize assistant message on abort
   */
  const finalizeOnAbort = useCallback((): void => {
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
  }, []);

  /**
   * Send a message to the Claude API
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

    // Create abort controller
    abortController.current = new AbortController();
    const signal = abortController.current.signal;

    try {
      const endpoint = sessionId
        ? `${apiBaseUrl}/conversations/${sessionId}/stream`
        : `${apiBaseUrl}/conversations`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ content }),
        signal,
      });

      if (!response.ok) {
        let errorMessage = `HTTP error: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.error || errorMessage;
        } catch {
          // Use default error message
        }
        throw new Error(errorMessage);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      await parseSSEStream(response.body, handleSSEEvent, signal);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        finalizeOnAbort();
        setIsStreaming(false);
        setIsLoading(false);
        return;
      }

      const errorMessage = getErrorMessage(err);
      setError(errorMessage);
      onError?.(errorMessage);
      removeEmptyAssistantMessage();
      setIsStreaming(false);
      setIsLoading(false);
    } finally {
      abortController.current = null;
    }
  }, [apiBaseUrl, sessionId, isLoading, handleSSEEvent, onError, finalizeOnAbort, removeEmptyAssistantMessage]);

  /**
   * Interrupt the current streaming response
   */
  const interrupt = useCallback(async (): Promise<void> => {
    if (abortController.current) {
      abortController.current.abort();
      abortController.current = null;
    }

    // Call interrupt endpoint if we have a session
    if (sessionId) {
      try {
        await fetch(`${apiBaseUrl}/conversations/${sessionId}/interrupt`, {
          method: 'POST',
        });
      } catch {
        // Ignore interrupt endpoint errors - abort is the primary mechanism
      }
    }

    setIsStreaming(false);
    setIsLoading(false);
  }, [apiBaseUrl, sessionId]);

  /**
   * Clear all messages and reset state
   */
  const clearMessages = useCallback((): void => {
    if (abortController.current) {
      abortController.current.abort();
      abortController.current = null;
    }

    setMessages([]);
    setSessionId(null);
    setError(null);
    setTurnCount(0);
    setTotalCostUsd(undefined);
    setIsLoading(false);
    setIsStreaming(false);
    currentAssistantMessageId.current = null;
    accumulatedText.current = '';
  }, []);

  /**
   * Resume an existing session by loading its history
   */
  const resumeSession = useCallback(async (targetSessionId: string): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const historyResponse = await fetch(`${apiBaseUrl}/sessions/${targetSessionId}/history`);

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
  }, [apiBaseUrl, onError]);

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

    // Actions
    sendMessage,
    interrupt,
    clearMessages,
    resumeSession,
    startNewSession,

    // Refs
    abortController,
  };
}

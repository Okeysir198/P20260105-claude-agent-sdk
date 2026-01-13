'use client';

import { useState, useCallback, useRef } from 'react';
import type { Message } from '@/types/messages';
import {
  createUserMessage,
  createAssistantMessage,
  createToolUseMessage,
  createToolResultMessage,
  createMessageId,
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
  /** Array of all messages in the conversation */
  messages: Message[];
  /** Current session ID, null if no session */
  sessionId: string | null;
  /** Whether a request is in progress */
  isLoading: boolean;
  /** Whether content is actively streaming */
  isStreaming: boolean;
  /** Current error message, null if no error */
  error: string | null;
  /** Number of completed conversation turns */
  turnCount: number;
  /** Total API cost in USD */
  totalCostUsd: number | undefined;

  // Actions
  /** Send a message to the assistant */
  sendMessage: (content: string) => Promise<void>;
  /** Interrupt the current streaming response */
  interrupt: () => Promise<void>;
  /** Clear all messages and reset state */
  clearMessages: () => void;
  /** Resume an existing session by ID */
  resumeSession: (sessionId: string) => Promise<void>;
  /** Start a fresh new session */
  startNewSession: () => void;

  // Refs
  /** AbortController ref for external access */
  abortController: React.MutableRefObject<AbortController | null>;
}

/**
 * Main hook for managing Claude chat conversations with SSE streaming.
 *
 * This hook provides complete conversation management including:
 * - Sending messages and streaming responses
 * - Tool use and tool result handling
 * - Session management (create, resume, clear)
 * - Interrupt/abort functionality
 *
 * @example
 * ```typescript
 * function ChatPage() {
 *   const {
 *     messages,
 *     isStreaming,
 *     sendMessage,
 *     interrupt,
 *     startNewSession,
 *   } = useClaudeChat({
 *     onError: (error) => console.error(error),
 *     onDone: (turns, cost) => console.log(`Done! Turns: ${turns}, Cost: $${cost}`),
 *   });
 *
 *   const handleSubmit = async (text: string) => {
 *     await sendMessage(text);
 *   };
 *
 *   return (
 *     <div>
 *       <MessageList messages={messages} />
 *       <ChatInput onSubmit={handleSubmit} disabled={isStreaming} />
 *       {isStreaming && <button onClick={interrupt}>Stop</button>}
 *     </div>
 *   );
 * }
 * ```
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
  const updateAssistantMessage = useCallback((text: string, isComplete: boolean = false) => {
    const messageId = currentAssistantMessageId.current;
    if (!messageId) return;

    setMessages((prev) => {
      return prev.map((msg) => {
        if (msg.id === messageId && msg.role === 'assistant') {
          return {
            ...msg,
            content: text,
            isStreaming: !isComplete,
          };
        }
        return msg;
      });
    });
  }, []);

  /**
   * Handle individual SSE events
   */
  const handleSSEEvent = useCallback((event: ParsedSSEEvent) => {
    console.log('[useClaudeChat] SSE Event:', event.type, event.data);
    switch (event.type) {
      case 'session_id': {
        const newSessionId = event.data.session_id;
        console.log('[useClaudeChat] Setting session ID:', newSessionId);
        setSessionId(newSessionId);
        onSessionCreated?.(newSessionId);
        break;
      }

      case 'text_delta': {
        // Accumulate text and update the current assistant message
        accumulatedText.current += event.data.text;
        updateAssistantMessage(accumulatedText.current);
        break;
      }

      case 'tool_use': {
        // Finalize any current assistant message before tool use
        if (accumulatedText.current && currentAssistantMessageId.current) {
          updateAssistantMessage(accumulatedText.current, true);
        }

        // Add tool use message
        const toolUseMessage = createToolUseMessage(
          event.data.tool_name,
          event.data.input,
          createMessageId() // Generate a tool_use_id for linking
        );
        setMessages((prev) => [...prev, toolUseMessage]);
        break;
      }

      case 'tool_result': {
        // Add tool result message
        const toolResultMessage = createToolResultMessage(
          event.data.tool_use_id,
          event.data.content,
          event.data.is_error
        );
        setMessages((prev) => [...prev, toolResultMessage]);

        // After tool result, create a new assistant message for continued response
        accumulatedText.current = '';
        const newAssistantMessage = createAssistantMessage('', true);
        currentAssistantMessageId.current = newAssistantMessage.id;
        setMessages((prev) => [...prev, newAssistantMessage]);
        break;
      }

      case 'done': {
        // Finalize the assistant message
        if (currentAssistantMessageId.current) {
          updateAssistantMessage(accumulatedText.current, true);
        }

        // Update turn count and cost
        setTurnCount(event.data.turn_count);
        if (event.data.total_cost_usd !== undefined) {
          setTotalCostUsd(event.data.total_cost_usd);
        }

        // Notify completion
        onDone?.(event.data.turn_count, event.data.total_cost_usd);

        // Clean up streaming state
        setIsStreaming(false);
        setIsLoading(false);
        currentAssistantMessageId.current = null;
        accumulatedText.current = '';
        break;
      }

      case 'error': {
        const errorMessage = event.data.error;
        setError(errorMessage);
        onError?.(errorMessage);
        setIsStreaming(false);
        setIsLoading(false);
        break;
      }
    }
  }, [updateAssistantMessage, onSessionCreated, onDone, onError]);

  /**
   * Send a message to the Claude API
   */
  const sendMessage = useCallback(async (content: string): Promise<void> => {
    if (!content.trim() || isLoading) return;

    // Clear any previous errors
    setError(null);
    setIsLoading(true);
    setIsStreaming(true);

    // Add user message to the conversation
    const userMessage = createUserMessage(content);
    setMessages((prev) => [...prev, userMessage]);

    // Create a new assistant message placeholder for streaming
    accumulatedText.current = '';
    const assistantMessage = createAssistantMessage('', true);
    currentAssistantMessageId.current = assistantMessage.id;
    setMessages((prev) => [...prev, assistantMessage]);

    // Create abort controller for this request
    abortController.current = new AbortController();
    const signal = abortController.current.signal;

    try {
      // Determine endpoint based on whether we have an existing session
      const endpoint = sessionId
        ? `${apiBaseUrl}/conversations/${sessionId}/stream`
        : `${apiBaseUrl}/conversations`;

      console.log('[useClaudeChat] Sending message:', { sessionId, endpoint, content });

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
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

      console.log('[useClaudeChat] Response OK, starting SSE stream processing');

      // Process the SSE stream
      await parseSSEStream(response.body, handleSSEEvent, signal);
      console.log('[useClaudeChat] SSE stream processing complete');

    } catch (err) {
      // Handle abort/interrupt
      if (err instanceof Error && err.name === 'AbortError') {
        // Remove the empty streaming assistant message
        setMessages((prev) => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage?.role === 'assistant' && !lastMessage.content) {
            return prev.slice(0, -1);
          }
          // Otherwise finalize the message with what we have
          return prev.map((msg) => {
            if (msg.id === currentAssistantMessageId.current && msg.role === 'assistant') {
              return { ...msg, isStreaming: false };
            }
            return msg;
          });
        });
        setIsStreaming(false);
        setIsLoading(false);
        return;
      }

      // Handle other errors
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
      setError(errorMessage);
      onError?.(errorMessage);

      // Remove the empty streaming assistant message
      setMessages((prev) => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage?.role === 'assistant' && !lastMessage.content) {
          return prev.slice(0, -1);
        }
        return prev;
      });

      setIsStreaming(false);
      setIsLoading(false);
    } finally {
      abortController.current = null;
    }
  }, [apiBaseUrl, sessionId, isLoading, handleSSEEvent, onError]);

  /**
   * Interrupt the current streaming response
   */
  const interrupt = useCallback(async (): Promise<void> => {
    if (abortController.current) {
      abortController.current.abort();
      abortController.current = null;
    }

    // Also call the interrupt endpoint if we have a session
    if (sessionId) {
      try {
        await fetch(`${apiBaseUrl}/conversations/${sessionId}/interrupt`, {
          method: 'POST',
        });
      } catch {
        // Ignore interrupt endpoint errors - the abort is the primary mechanism
      }
    }

    setIsStreaming(false);
    setIsLoading(false);
  }, [apiBaseUrl, sessionId]);

  /**
   * Clear all messages and reset state
   */
  const clearMessages = useCallback(() => {
    // Abort any ongoing request
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
      // First, try to resume the session
      const resumeResponse = await fetch(`${apiBaseUrl}/sessions/${targetSessionId}/resume`, {
        method: 'POST',
      });

      if (!resumeResponse.ok) {
        throw new Error(`Failed to resume session: ${resumeResponse.status}`);
      }

      // Get session details including message history
      const sessionResponse = await fetch(`${apiBaseUrl}/sessions/${targetSessionId}`);

      if (!sessionResponse.ok) {
        throw new Error(`Failed to fetch session: ${sessionResponse.status}`);
      }

      const sessionData = await sessionResponse.json();

      // Set session ID
      setSessionId(targetSessionId);

      // Load messages from session history if available
      if (sessionData.messages && Array.isArray(sessionData.messages)) {
        // Transform backend messages to frontend format
        const loadedMessages: Message[] = sessionData.messages.map((msg: Record<string, unknown>) => {
          const baseMessage = {
            id: (msg.id as string) || createMessageId(),
            timestamp: new Date((msg.timestamp as string) || Date.now()),
          };

          switch (msg.role) {
            case 'user':
              return {
                ...baseMessage,
                role: 'user' as const,
                content: msg.content as string,
              };
            case 'assistant':
              return {
                ...baseMessage,
                role: 'assistant' as const,
                content: msg.content as string,
                isStreaming: false,
              };
            case 'tool_use':
              return {
                ...baseMessage,
                role: 'tool_use' as const,
                toolName: msg.tool_name as string,
                input: (msg.input as Record<string, unknown>) || {},
                toolUseId: msg.tool_use_id as string,
              };
            case 'tool_result':
              return {
                ...baseMessage,
                role: 'tool_result' as const,
                toolUseId: msg.tool_use_id as string,
                content: msg.content as string,
                isError: (msg.is_error as boolean) ?? false,
              };
            default:
              return {
                ...baseMessage,
                role: 'assistant' as const,
                content: String(msg.content || ''),
                isStreaming: false,
              };
          }
        });

        setMessages(loadedMessages);
      }

      // Update turn count if available
      if (sessionData.turn_count !== undefined) {
        setTurnCount(sessionData.turn_count);
      }

      if (sessionData.total_cost_usd !== undefined) {
        setTotalCostUsd(sessionData.total_cost_usd);
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to resume session';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl, onError]);

  /**
   * Start a fresh new session
   */
  const startNewSession = useCallback(() => {
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

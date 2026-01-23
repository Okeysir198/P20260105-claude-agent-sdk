'use client';

import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useWebSocket } from './use-websocket';
import { useQueryClient } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/constants';
import type { WebSocketEvent, ReadyEvent, TextDeltaEvent, ChatMessage } from '@/types';
import { toast } from 'sonner';

export function useChat() {
  const {
    messages,
    sessionId,
    agentId,
    addMessage,
    updateLastMessage,
    setStreaming,
    setSessionId,
    setConnectionStatus
  } = useChatStore();

  const ws = useWebSocket();
  const queryClient = useQueryClient();
  const assistantMessageStarted = useRef(false);
  const pendingSessionId = useRef<string | null>(null);

  // Connect to WebSocket when agent changes, disconnect when agentId is null
  useEffect(() => {
    if (agentId) {
      // Store pending sessionId for error handling
      pendingSessionId.current = sessionId;
      ws.connect(agentId, sessionId);
    } else {
      // Disconnect when no agent is selected (e.g., "New Chat" button)
      ws.disconnect();
      setConnectionStatus('disconnected');
    }
  }, [agentId]);

  // Reset assistant message flag when sending new message
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.role === 'user') {
      assistantMessageStarted.current = false;
    }
  }, [messages]);

  // Handle WebSocket events
  useEffect(() => {
    const unsubscribe = ws.onMessage((event: WebSocketEvent) => {
      switch (event.type) {
        case 'ready':
          setConnectionStatus('connected');
          if (event.session_id) {
            setSessionId(event.session_id);
            pendingSessionId.current = null;
            // Refresh sessions list to show new session
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
          }
          break;

        case 'session_id':
          setSessionId(event.session_id);
          pendingSessionId.current = null;
          // Refresh sessions list to show new session
          queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
          break;

        case 'text_delta':
          // Filter out tool reference patterns like [Tool: Bash (ID: call_...)] Input: {...}
          const toolRefPattern = /\[Tool: [^]]+\] Input:\s*(?:\{[^}]*\}|\[.*?\]|"[^"]*")\s*/g;
          const filteredText = event.text.replace(toolRefPattern, '');

          // Create assistant message on first text delta if it doesn't exist
          // or if the last message wasn't an assistant message (e.g., after tool calls)
          const lastMessage = messages[messages.length - 1];
          const shouldCreateNew = !assistantMessageStarted.current ||
            (lastMessage && lastMessage.role !== 'assistant');

          if (shouldCreateNew) {
            const assistantMessage: ChatMessage = {
              id: crypto.randomUUID(),
              role: 'assistant',
              content: filteredText,
              timestamp: new Date(),
            };
            addMessage(assistantMessage);
            assistantMessageStarted.current = true;
          } else {
            // Update the last message (which should be the assistant message)
            updateLastMessage((msg) => ({
              ...msg,
              content: msg.content + filteredText,
            }));
          }
          break;

        case 'tool_use':
          // Reset assistant message flag so next text_delta creates a new message
          assistantMessageStarted.current = false;
          addMessage({
            id: event.id,
            role: 'tool_use',
            content: '',
            timestamp: new Date(),
            toolName: event.name,
            toolInput: event.input,
          });
          break;

        case 'tool_result':
          // Reset assistant message flag so next text_delta creates a new message
          assistantMessageStarted.current = false;
          addMessage({
            id: crypto.randomUUID(),
            role: 'tool_result',
            content: event.content,
            timestamp: new Date(),
            toolUseId: event.tool_use_id,
            isError: event.is_error,
          });
          break;

        case 'done':
          setStreaming(false);
          assistantMessageStarted.current = false;
          break;

        case 'error':
          console.error('WebSocket error:', event.error);
          setStreaming(false);
          setConnectionStatus('error');
          assistantMessageStarted.current = false;

          // Handle session not found error
          if (event.error?.includes('not found') && pendingSessionId.current) {
            toast.error('Session not found. Starting a new conversation...');
            // Clear the invalid session ID and reconnect
            const invalidSessionId = pendingSessionId.current;
            pendingSessionId.current = null;
            setSessionId(null);
            // Reconnect without sessionId to start fresh
            setTimeout(() => {
              ws.connect(agentId, null);
            }, 1000);
          } else {
            toast.error(event.error || 'An error occurred');
          }
          break;
      }
    });

    return () => {
      unsubscribe?.();
    };
  }, [ws, updateLastMessage, addMessage, setSessionId, setStreaming, setConnectionStatus, agentId, messages, queryClient]);

  const sendMessage = useCallback((content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    addMessage(userMessage);
    assistantMessageStarted.current = false;
    setStreaming(true);
    ws.sendMessage(content);
  }, [addMessage, setStreaming, ws]);

  const disconnect = useCallback(() => {
    ws.disconnect();
  }, [ws]);

  return {
    messages,
    sessionId,
    agentId,
    status: ws.status,
    sendMessage,
    disconnect,
    isStreaming: useChatStore((s) => s.isStreaming),
  };
}

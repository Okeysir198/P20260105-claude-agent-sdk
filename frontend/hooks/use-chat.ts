'use client';

import { useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { useChatStore } from '@/lib/store/chat-store';
import { useWebSocket } from './use-websocket';
import type { ContentBlock } from '@/types';
import { validateMessageContent } from '@/lib/message-utils';
import { createEventHandler, type EventHandlerContext } from './chat-event-handlers';
import { createUserMessage } from './chat-message-factory';

export function useChat() {
  const {
    messages,
    sessionId,
    agentId,
    addMessage,
    updateLastMessage,
    setMessages,
    setStreaming,
    setSessionId,
    setConnectionStatus,
    pendingMessage,
    setPendingMessage,
    setCancelling,
    setCompacting
  } = useChatStore();

  const ws = useWebSocket();
  const queryClient = useQueryClient();
  const assistantMessageStarted = useRef(false);
  const pendingMessageRef = useRef<string | null>(null);
  const prevSessionIdForDeleteRef = useRef<string | null>(null);

  // Keep ref in sync with store value
  useEffect(() => {
    pendingMessageRef.current = pendingMessage;
  }, [pendingMessage]);

  // Connect to WebSocket when agent changes, disconnect when agentId is null
  // Intentionally only depend on agentId - sessionId is used for initial connection
  // but we don't want to reconnect when sessionId changes from ready event
  useEffect(() => {
    if (agentId) {
      ws.connect(agentId, sessionId);
    } else {
      ws.disconnect();
      setConnectionStatus('disconnected');
    }
    // Only depend on agentId - this handles agent selection/change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  // Handle session deletion: when sessionId goes from a value to null while agentId is set
  // This needs a separate effect to detect the transition and force reconnect
  useEffect(() => {
    const prevSessionId = prevSessionIdForDeleteRef.current;
    prevSessionIdForDeleteRef.current = sessionId;

    // Detect session deletion: sessionId changed from a value to null
    // Use forceReconnect to bypass the 500ms delay for immediate new session
    if (agentId && prevSessionId !== null && sessionId === null) {
      ws.forceReconnect(agentId, null);
    }
  }, [sessionId, agentId, ws]);

  // Reset assistant message flag when sending new message
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.role === 'user') {
      assistantMessageStarted.current = false;
    }
  }, [messages]);

  // Handle WebSocket events
  useEffect(() => {
    // Create the event handler with context
    const eventContext: EventHandlerContext = {
      store: {
        setConnectionStatus,
        setSessionId,
        setStreaming,
        setCancelling,
        setCompacting,
        setPendingMessage,
        addMessage,
        updateLastMessage,
        setMessages,
      },
      ws,
      queryClient,
      agentId,
      assistantMessageStarted,
      pendingMessageRef,
    };

    const handleEvent = createEventHandler(eventContext);
    const unsubscribe = ws.onMessage(handleEvent);

    return () => {
      unsubscribe?.();
    };
  }, [
    ws,
    setConnectionStatus,
    setSessionId,
    setStreaming,
    setCancelling,
    setCompacting,
    setPendingMessage,
    addMessage,
    updateLastMessage,
    setMessages,
    queryClient,
    agentId,
  ]);

  /** Send a text or multi-part (text + images) message to the chat. */
  const sendMessage = useCallback((content: string | ContentBlock[]) => {
    try {
      const validation = validateMessageContent(content);
      if (!validation.valid) {
        throw new Error(validation.error);
      }

      addMessage(createUserMessage(content));
      assistantMessageStarted.current = false;
      setStreaming(true);
      ws.sendMessage(content);
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to send message');
    }
  }, [addMessage, setStreaming, ws]);

  const disconnect = useCallback(() => {
    ws.disconnect();
  }, [ws]);

  const sendAnswer = useCallback((questionId: string, answers: Record<string, string | string[]>) => {
    ws.sendAnswer(questionId, answers);
  }, [ws]);

  const sendPlanApproval = useCallback((planId: string, approved: boolean, feedback?: string) => {
    ws.sendPlanApproval(planId, approved, feedback);
  }, [ws]);

  const cancelStream = useCallback(() => {
    if (useChatStore.getState().isStreaming) {
      useChatStore.getState().setCancelling(true);
      ws.sendCancel();
    }
  }, [ws]);

  const compactContext = useCallback(() => {
    if (!useChatStore.getState().isCompacting) {
      ws.sendCompact();
    }
  }, [ws]);

  return {
    messages,
    sessionId,
    agentId,
    status: ws.status,
    sendMessage,
    sendAnswer,
    sendPlanApproval,
    cancelStream,
    compactContext,
    disconnect,
    isStreaming: useChatStore((s) => s.isStreaming),
    isCancelling: useChatStore((s) => s.isCancelling),
    isCompacting: useChatStore((s) => s.isCompacting),
  };
}

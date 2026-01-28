'use client';

import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useQuestionStore } from '@/lib/store/question-store';
import { usePlanStore, type UIPlanStep } from '@/lib/store/plan-store';
import { useWebSocket } from './use-websocket';
import { useQueryClient } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/constants';
import type { WebSocketEvent, ReadyEvent, TextDeltaEvent, ChatMessage, AskUserQuestionEvent, PlanApprovalEvent, UIQuestion } from '@/types';
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
    setConnectionStatus,
    pendingMessage,
    setPendingMessage
  } = useChatStore();

  const { openModal: openQuestionModal } = useQuestionStore();
  const { openModal: openPlanModal } = usePlanStore();

  const ws = useWebSocket();
  const queryClient = useQueryClient();
  const assistantMessageStarted = useRef(false);
  const pendingSessionId = useRef<string | null>(null);
  const pendingMessageRef = useRef<string | null>(null);
  const prevSessionIdForDeleteRef = useRef<string | null>(null);

  // Keep ref in sync with store value
  useEffect(() => {
    pendingMessageRef.current = pendingMessage;
  }, [pendingMessage]);

  // Connect to WebSocket when agent changes, disconnect when agentId is null
  useEffect(() => {
    if (agentId) {
      pendingSessionId.current = sessionId;
      ws.connect(agentId, sessionId);
    } else {
      ws.disconnect();
      setConnectionStatus('disconnected');
    }
  }, [agentId]); // Only depend on agentId - this handles agent selection/change

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
  }, [sessionId, agentId]);

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

          // Send pending message if there is one (from welcome page)
          if (pendingMessageRef.current) {
            const messageToSend = pendingMessageRef.current;
            setPendingMessage(null);
            pendingMessageRef.current = null;

            // Create and add user message
            const userMessage: ChatMessage = {
              id: crypto.randomUUID(),
              role: 'user',
              content: messageToSend,
              timestamp: new Date(),
            };
            addMessage(userMessage);
            assistantMessageStarted.current = false;
            setStreaming(true);
            ws.sendMessage(messageToSend);
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
          // Get fresh messages from store to avoid closure staleness
          const currentMessages = useChatStore.getState().messages;
          const lastMessage = currentMessages[currentMessages.length - 1];
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

        case 'ask_user_question':
          // Transform WebSocket Question format to UI Question format
          const wsEvent = event as AskUserQuestionEvent;
          const transformedQuestions: UIQuestion[] = wsEvent.questions.map((q) => ({
            question: q.question,
            options: q.options.map((opt) => ({
              value: opt.label,
              description: opt.description,
            })),
            allowMultiple: q.multiSelect,
          }));
          openQuestionModal(wsEvent.question_id, transformedQuestions, wsEvent.timeout);
          break;

        case 'plan_approval':
          // Transform WebSocket PlanApprovalEvent to UI format
          const planEvent = event as PlanApprovalEvent;
          const transformedSteps: UIPlanStep[] = planEvent.steps.map((s) => ({
            description: s.description,
            status: s.status || 'pending',
          }));
          openPlanModal(
            planEvent.plan_id,
            planEvent.title,
            planEvent.summary,
            transformedSteps,
            planEvent.timeout
          );
          break;

        case 'error':
          setStreaming(false);
          assistantMessageStarted.current = false;

          // Handle session not found error - this is recoverable
          if (event.error?.includes('not found') && event.error?.includes('Session')) {
            console.warn('Session not found, starting fresh:', event.error);
            // Don't set error status - we're recovering
            setConnectionStatus('connecting');
            toast.info('Session expired. Starting a new conversation...');
            // Clear the invalid session ID and reconnect
            pendingSessionId.current = null;
            setSessionId(null);
            // Refresh sessions list to remove the invalid session
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
            // Reconnect without sessionId to start fresh
            setTimeout(() => {
              ws.connect(agentId, null);
            }, 500);
          } else {
            // Non-recoverable error
            console.error('WebSocket error:', event.error);
            setConnectionStatus('error');
            toast.error(event.error || 'An error occurred');
          }
          break;
      }
    });

    return () => {
      unsubscribe?.();
    };
  }, [ws, updateLastMessage, addMessage, setSessionId, setStreaming, setConnectionStatus, setPendingMessage, agentId, queryClient]);

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

  const sendAnswer = useCallback((questionId: string, answers: Record<string, string | string[]>) => {
    ws.sendAnswer(questionId, answers);
  }, [ws]);

  const sendPlanApproval = useCallback((planId: string, approved: boolean, feedback?: string) => {
    ws.sendPlanApproval(planId, approved, feedback);
  }, [ws]);

  return {
    messages,
    sessionId,
    agentId,
    status: ws.status,
    sendMessage,
    sendAnswer,
    sendPlanApproval,
    disconnect,
    isStreaming: useChatStore((s) => s.isStreaming),
  };
}

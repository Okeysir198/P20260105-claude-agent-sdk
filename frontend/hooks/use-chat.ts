'use client';

import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '@/lib/store/chat-store';
import { useMessageQueueStore } from '@/lib/store/message-queue-store';
import { useQuestionStore } from '@/lib/store/question-store';
import { usePlanStore, type UIPlanStep } from '@/lib/store/plan-store';
import { useWebSocket } from './use-websocket';
import { useQueryClient } from '@tanstack/react-query';
import { QUERY_KEYS } from '@/lib/constants';
import type { WebSocketEvent, ChatMessage, AskUserQuestionEvent, PlanApprovalEvent, UIQuestion } from '@/types';
import { toast } from 'sonner';
import { WebSocketErrorCode } from '@/types/websocket';
import type { TabMessage } from '@/lib/broadcast-channel';

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
            // Reset session stats for new session, or initialize with existing turn count for resumed
            if (!event.resumed) {
              useChatStore.getState().resetSessionStats();
            } else if (event.turn_count) {
              // Initialize stats for resumed session with existing turn count
              useChatStore.getState().setSessionStats({
                totalCost: 0,
                turnCount: event.turn_count,
                startTime: new Date(),
              });
            }
            // Refresh sessions list to show new session
            queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
          }

          // Check if there are queued messages and inform user
          const queueLength = useMessageQueueStore.getState().getQueueLength();
          if (queueLength > 0) {
            toast.info(`Sending ${queueLength} queued message${queueLength > 1 ? 's' : ''}...`);
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
          // Track session stats (cumulative cost and turn count)
          if (event.turn_count !== undefined) {
            const currentStats = useChatStore.getState().sessionStats;
            useChatStore.getState().setSessionStats({
              totalCost: (currentStats?.totalCost || 0) + (event.total_cost_usd || 0),
              turnCount: event.turn_count,
              startTime: currentStats?.startTime || new Date(),
            });
          }
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

          // Handle structured error codes
          switch (event.code) {
            case WebSocketErrorCode.SESSION_NOT_FOUND:
              console.warn('Session not found, starting fresh:', event.error);
              setConnectionStatus('connecting');
              toast.info('Session expired. Starting a new conversation...');
              pendingSessionId.current = null;
              setSessionId(null);
              queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
              setTimeout(() => {
                ws.connect(agentId, null);
              }, 500);
              break;

            case WebSocketErrorCode.TOKEN_EXPIRED:
            case WebSocketErrorCode.TOKEN_INVALID:
              console.warn('Token error:', event.error);
              setConnectionStatus('connecting');
              toast.info('Authentication expired. Reconnecting...');
              break;

            case WebSocketErrorCode.RATE_LIMITED:
              console.warn('Rate limited:', event.error);
              setConnectionStatus('error');
              toast.error(event.error || 'Rate limit exceeded. Please wait.');
              break;

            case WebSocketErrorCode.AGENT_NOT_FOUND:
              console.error('Agent not found:', event.error);
              setConnectionStatus('error');
              toast.error(event.error || 'Agent not found');
              break;

            default:
              // Handle legacy string-based error detection
              if (event.error?.includes('not found') && event.error?.includes('Session')) {
                console.warn('Session not found (legacy), starting fresh:', event.error);
                setConnectionStatus('connecting');
                toast.info('Session expired. Starting a new conversation...');
                pendingSessionId.current = null;
                setSessionId(null);
                queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
                setTimeout(() => {
                  ws.connect(agentId, null);
                }, 500);
              } else {
                console.error('WebSocket error:', event.error);
                setConnectionStatus('error');
                toast.error(event.error || 'An error occurred');
              }
          }
          break;
      }
    });

    return () => {
      unsubscribe?.();
    };
  }, [ws, updateLastMessage, addMessage, setSessionId, setStreaming, setConnectionStatus, setPendingMessage, agentId, queryClient]);

  // Handle cross-tab state synchronization
  useEffect(() => {
    // Dynamic import to avoid SSR issues
    let unregister: (() => void) | undefined;

    import('@/lib/broadcast-channel').then(({ getTabBroadcastChannel }) => {
      const channel = getTabBroadcastChannel();

      // If we're leader, listen for sync requests from followers
      if (channel.getIsLeader()) {
        unregister = channel.onMessage((message: TabMessage) => {
          if (message.type === 'sync-state') {
            // Broadcast our current state to the requesting tab
            channel.broadcastState({
              sessionId,
              agentId,
              messages,
              connectionStatus: ws.status,
            });
          }
        });
      } else {
        // If we're follower, listen for sync responses from leader
        unregister = channel.onMessage((message: TabMessage) => {
          if (message.type === 'sync-state' && message.state) {
            // Sync the state from leader
            if (message.state.sessionId !== sessionId) {
              setSessionId(message.state.sessionId);
            }
            if (message.state.agentId !== agentId) {
              useChatStore.getState().setAgentId(message.state.agentId);
            }
            if (message.state.connectionStatus !== ws.status) {
              setConnectionStatus(message.state.connectionStatus as any);
            }
            // Note: We don't sync messages to avoid conflicts
            // Messages are synced via the new-message event type
          }
        });
      }
    });

    return () => {
      unregister?.();
    };
  }, [ws, sessionId, agentId, messages, setSessionId, setConnectionStatus]);

  const sendMessage = useCallback((content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    // Check if WebSocket is connected
    const isConnected = ws.status === 'connected';

    addMessage(userMessage);

    if (isConnected) {
      // Send immediately if connected
      assistantMessageStarted.current = false;
      setStreaming(true);
      ws.sendMessage(content);
    } else {
      // Enqueue message if disconnected (ws.sendMessage will handle this)
      // Just show a toast to inform the user
      const queueLength = useMessageQueueStore.getState().getQueueLength();
      toast.info(
        `Message queued. Will send when connected (${queueLength + 1} message${queueLength > 0 ? 's' : ''} in queue)`,
        { id: 'message-queued' }
      );
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

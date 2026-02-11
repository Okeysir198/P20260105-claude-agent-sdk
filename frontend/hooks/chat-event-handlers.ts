/**
 * WebSocket event handlers for chat functionality.
 * Each handler processes a specific WebSocket event type and updates the chat store.
 *
 * @module chat-event-handlers
 */

import type { QueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import type { WebSocketEvent, ReadyEvent, CompactCompletedEvent } from '@/types';
import type { DoneEvent } from '@/types/websocket';
import type { ChatStore } from './chat-store-types';
import { QUERY_KEYS } from '@/lib/constants';
import { validateMessageContent } from '@/lib/message-utils';
import {
  createUserMessage,
  createAssistantMessage,
  createToolUseMessage,
  createToolResultMessage
} from './chat-message-factory';
import { filterToolReferences } from './chat-text-utils';
import type { UIQuestion } from '@/types';
import type { UIPlanStep } from '@/lib/store/plan-store';

/**
 * WebSocket interface required by event handlers.
 * Matches the return type of useWebSocket() hook.
 */
export interface WebSocketClient {
  connect: (agentId: string | null, sessionId?: string | null) => void;
  sendMessage: (content: string | import('@/types').ContentBlock[]) => void;
}

/**
 * Context and state passed to event handlers.
 */
export interface EventHandlerContext {
  store: ChatStore;
  ws: WebSocketClient;
  queryClient: QueryClient;
  agentId: string | null;
  assistantMessageStarted: React.MutableRefObject<boolean>;
  pendingMessageRef: React.MutableRefObject<string | null>;
}

/**
 * Handles the 'ready' event - WebSocket connection is ready.
 * Sets session ID, sends pending message if any exists.
 */
export function handleReadyEvent(
  event: ReadyEvent,
  ctx: EventHandlerContext
): void {
  const { store, queryClient, pendingMessageRef } = ctx;

  store.setConnectionStatus('connected');

  if (event.session_id) {
    store.setSessionId(event.session_id);
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
  }

  // Send pending message if there is one (from welcome page)
  if (pendingMessageRef.current) {
    sendPendingMessage(pendingMessageRef.current, ctx);
    pendingMessageRef.current = null;
    store.setPendingMessage(null);
  }
}

/**
 * Sends a pending message that was queued before connection.
 */
function sendPendingMessage(messageContent: string, ctx: EventHandlerContext): void {
  const { store, ws } = ctx;

  try {
    const validation = validateMessageContent(messageContent);

    if (!validation.valid) {
      throw new Error(validation.error);
    }

    const userMessage = createUserMessage(messageContent);
    store.addMessage(userMessage);
    ctx.assistantMessageStarted.current = false;
    store.setStreaming(true);
    ws.sendMessage(messageContent);
  } catch (error) {
    console.error('Failed to send pending message:', error);
    toast.error(error instanceof Error ? error.message : 'Failed to send message');
  }
}

/**
 * Handles the 'session_id' event - new or resumed session.
 */
export function handleSessionIdEvent(
  sessionId: string,
  ctx: EventHandlerContext
): void {
  const { store, queryClient } = ctx;

  store.setSessionId(sessionId);
  queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
}

/**
 * Handles the 'text_delta' event - streaming text from assistant.
 */
export function handleTextDeltaEvent(
  text: string,
  ctx: EventHandlerContext
): void {
  const { store } = ctx;
  const filteredText = filterToolReferences(text);
  const currentMessages = store.messages;
  const lastMessage = currentMessages[currentMessages.length - 1];

  const shouldCreateNew = !ctx.assistantMessageStarted.current ||
    (lastMessage && lastMessage.role !== 'assistant');

  if (shouldCreateNew) {
    const assistantMessage = createAssistantMessage(filteredText);
    store.addMessage(assistantMessage);
    ctx.assistantMessageStarted.current = true;
  } else {
    store.updateLastMessage((msg) => ({
      ...msg,
      content: msg.content + filteredText,
    }));
  }
}

/**
 * Handles the 'assistant_text' event - canonical text from AssistantMessage TextBlock.
 * Replaces the last assistant message content with clean text that doesn't
 * contain proxy-injected serialized tool_use content.
 */
export function handleAssistantTextEvent(
  text: string,
  ctx: EventHandlerContext
): void {
  const { store } = ctx;
  const messages = store.messages;

  // Find the last assistant message and replace its content
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'assistant') {
      const updated = [...messages];
      updated[i] = { ...updated[i], content: text };
      store.setMessages(updated);
      break;
    }
  }
}

/**
 * Handles the 'tool_use' event - agent is calling a tool.
 */
export function handleToolUseEvent(
  id: string,
  name: string,
  input: Record<string, unknown>,
  parentToolUseId: string | undefined,
  ctx: EventHandlerContext
): void {
  const { store } = ctx;

  ctx.assistantMessageStarted.current = false;
  const message = createToolUseMessage(id, name, input, parentToolUseId);
  store.addMessage(message);
}

/**
 * Handles the 'tool_result' event - result from tool execution.
 */
export function handleToolResultEvent(
  toolUseId: string,
  content: string,
  isError: boolean | undefined,
  parentToolUseId: string | undefined,
  ctx: EventHandlerContext
): void {
  const { store } = ctx;

  ctx.assistantMessageStarted.current = false;
  const message = createToolResultMessage(toolUseId, content, isError, parentToolUseId);
  store.addMessage(message);
}

/**
 * Handles the 'done' event - stream completed.
 */
export function handleDoneEvent(event: DoneEvent, ctx: EventHandlerContext): void {
  const { store } = ctx;

  store.setStreaming(false);
  ctx.assistantMessageStarted.current = false;

  // Capture usage data in kanban store
  if (event.total_cost_usd !== undefined || event.usage) {
    import('@/lib/store/kanban-store').then(({ useKanbanStore }) => {
      useKanbanStore.getState().setSessionUsage({
        totalCostUsd: event.total_cost_usd || 0,
        durationMs: event.duration_ms || 0,
        durationApiMs: event.duration_api_ms || 0,
        turnCount: event.turn_count || 0,
        isError: event.is_error || false,
        inputTokens: event.usage?.input_tokens,
        outputTokens: event.usage?.output_tokens,
        cacheCreationInputTokens: event.usage?.cache_creation_input_tokens,
        cacheReadInputTokens: event.usage?.cache_read_input_tokens,
      });
    });
  }
}

/**
 * Handles the 'cancelled' event - stream was cancelled.
 */
export function handleCancelledEvent(ctx: EventHandlerContext): void {
  const { store } = ctx;

  store.setStreaming(false);
  store.setCancelling(false);
  ctx.assistantMessageStarted.current = false;
}

/**
 * Handles the 'compact_started' event - context compaction in progress.
 */
export function handleCompactStartedEvent(_ctx: EventHandlerContext): void {
  _ctx.store.setCompacting(true);
}

/**
 * Handles the 'compact_completed' event - context compaction finished.
 */
export function handleCompactCompletedEvent(
  event: CompactCompletedEvent,
  ctx: EventHandlerContext
): void {
  const { store } = ctx;

  store.setCompacting(false);

  if (event.session_id) {
    store.setSessionId(event.session_id);
  }
}

/**
 * Handles the 'ask_user_question' event - agent needs user input.
 */
export function handleAskUserQuestionEvent(
  questionId: string,
  questions: Array<{
    question: string;
    options: Array<{ label: string; description: string }>;
    multiSelect: boolean;
  }> | string,
  timeout: number,
  _ctx: EventHandlerContext
): void {
  // Handle case where backend sends questions as a JSON string instead of a parsed array
  let parsedQuestions: Array<{
    question: string;
    options: Array<{ label: string; description: string }>;
    multiSelect: boolean;
  }>;

  if (Array.isArray(questions)) {
    parsedQuestions = questions;
  } else if (typeof questions === 'string') {
    try {
      const parsed = JSON.parse(questions);
      if (Array.isArray(parsed)) {
        parsedQuestions = parsed;
      } else {
        console.error('[WebSocket] Parsed questions is not an array:', parsed);
        toast.error('Invalid question format received');
        return;
      }
    } catch (err) {
      console.error('[WebSocket] Failed to parse questions JSON string:', err);
      toast.error('Failed to parse question data');
      return;
    }
  } else {
    console.error('[WebSocket] Unexpected questions type:', typeof questions);
    toast.error('Invalid question format received');
    return;
  }

  // Transform WebSocket Question format to UI Question format
  const transformedQuestions: UIQuestion[] = parsedQuestions.map((q) => ({
    question: q.question,
    options: q.options.map((opt) => ({
      value: opt.label,
      description: opt.description,
    })),
    allowMultiple: q.multiSelect,
  }));

  // Import dynamically to avoid circular dependency
  console.log("[WebSocket] Opening AskUserQuestion modal", { questionId, transformedQuestions, timeout });
  import('@/lib/store/question-store').then(({ useQuestionStore }) => {
    useQuestionStore.getState().openModal(questionId, transformedQuestions, timeout);
    console.log("[WebSocket] AskUserQuestion modal opened successfully");
  }).catch((err) => {
    console.error('Failed to open question modal:', err);
    toast.error('Failed to open question dialog');
  });
}

/**
 * Handles the 'plan_approval' event - agent presents plan for approval.
 */
export function handlePlanApprovalEvent(
  planId: string,
  title: string,
  summary: string,
  steps: Array<{ description: string; status?: string }>,
  timeout: number,
  _ctx: EventHandlerContext
): void {
  // Transform WebSocket PlanStep to UIPlanStep format
  const transformedSteps: UIPlanStep[] = steps.map((s) => ({
    description: s.description,
    status: (s.status as UIPlanStep['status']) || 'pending',
  }));

  // Import dynamically to avoid circular dependency
  import('@/lib/store/plan-store').then(({ usePlanStore }) => {
    usePlanStore.getState().openModal(planId, title, summary, transformedSteps, timeout);
  }).catch((err) => {
    console.error('Failed to open plan approval modal:', err);
    toast.error('Failed to open plan approval dialog');
  });
}

/**
 * Handles the 'error' event - WebSocket or processing error.
 * Handles recoverable errors (like session not found) specially.
 */
export function handleErrorEvent(
  errorMessage: string | undefined,
  ctx: EventHandlerContext
): void {
  const { store, ws, queryClient, agentId } = ctx;

  store.setStreaming(false);
  ctx.assistantMessageStarted.current = false;

  // Handle session not found error - this is recoverable
  if (errorMessage?.includes('not found') && errorMessage?.includes('Session')) {
    console.warn('Session not found, starting fresh:', errorMessage);
    store.setConnectionStatus('connecting');
    toast.info('Session expired. Starting a new conversation...');
    store.setSessionId(null);
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });

    // Reconnect without sessionId to start fresh
    setTimeout(() => {
      ws.connect(agentId, null);
    }, 500);
  } else {
    // Non-recoverable error
    console.error('WebSocket error:', errorMessage);
    store.setConnectionStatus('error');
    toast.error(errorMessage || 'An error occurred');
  }
}

/**
 * Main event router - dispatches WebSocket events to appropriate handlers.
 */
export function createEventHandler(ctx: EventHandlerContext): (event: WebSocketEvent) => void {
  return function handleEvent(event: WebSocketEvent): void {
    switch (event.type) {
      case 'ready':
        handleReadyEvent(event, ctx);
        break;

      case 'session_id':
        handleSessionIdEvent(event.session_id, ctx);
        break;

      case 'text_delta':
        handleTextDeltaEvent(event.text, ctx);
        break;

      case 'assistant_text':
        handleAssistantTextEvent(event.text, ctx);
        break;

      case 'tool_use':
        handleToolUseEvent(event.id, event.name, event.input, event.parent_tool_use_id, ctx);
        break;

      case 'tool_result':
        handleToolResultEvent(event.tool_use_id, event.content, event.is_error, event.parent_tool_use_id, ctx);
        break;

      case 'done':
        handleDoneEvent(event, ctx);
        break;

      case 'cancelled':
        handleCancelledEvent(ctx);
        break;

      case 'compact_started':
        handleCompactStartedEvent(ctx);
        break;

      case 'compact_completed':
        handleCompactCompletedEvent(event, ctx);
        break;

      case 'ask_user_question':
        console.log("[WebSocket] Received ask_user_question event", event);
        handleAskUserQuestionEvent(
          event.question_id,
          event.questions,
          event.timeout,
          ctx
        );
        break;

      case 'plan_approval':
        handlePlanApprovalEvent(
          event.plan_id,
          event.title,
          event.summary,
          event.steps,
          event.timeout,
          ctx
        );
        break;

      case 'error':
        handleErrorEvent(event.error, ctx);
        break;
    }
  };
}

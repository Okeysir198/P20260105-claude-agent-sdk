import type { QueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import type { WebSocketEvent, ReadyEvent, CompactCompletedEvent } from '@/types';
import type { DoneEvent, FileUploadedEvent } from '@/types/websocket';
import type { ChatStore } from './chat-store-types';
import { QUERY_KEYS } from '@/lib/constants';
import { validateMessageContent } from '@/lib/message-utils';
import { extractText, normalizeToolResultContent } from '@/lib/content-utils';
import {
  createUserMessage,
  createAssistantMessage,
  createToolUseMessage,
  createToolResultMessage
} from './chat-message-factory';
import { filterToolReferences } from './chat-text-utils';
import type { UIPlanStep } from '@/lib/store/plan-store';
import { useChatStore } from '@/lib/store/chat-store';
import { normalizeQuestions, toUIQuestions } from '@/lib/question-utils';
import type { RawQuestion } from '@/lib/question-utils';


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

  // Store cwd_id immediately — available for file uploads before session_id
  if (event.cwd_id) {
    store.setCwdId(event.cwd_id);
  }

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
  const currentMessages = useChatStore.getState().messages;
  const lastMessage = currentMessages[currentMessages.length - 1];

  const shouldCreateNew = !ctx.assistantMessageStarted.current ||
    (lastMessage && lastMessage.role !== 'assistant');

  if (shouldCreateNew) {
    const assistantMessage = createAssistantMessage(filteredText);
    store.addMessage(assistantMessage);
    ctx.assistantMessageStarted.current = true;
  } else {
    store.updateLastMessage((msg) => {
      // Ensure content is string before concatenation to prevent [object Object]
      const existing = typeof msg.content === 'string' ? msg.content : extractText(msg.content);
      return { ...msg, content: existing + filteredText };
    });
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
  const messages = useChatStore.getState().messages;

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
  content: unknown,
  isError: boolean | undefined,
  parentToolUseId: string | undefined,
  ctx: EventHandlerContext
): void {
  const { store } = ctx;

  ctx.assistantMessageStarted.current = false;
  // Normalize content to string — backend may send arrays of content blocks
  const normalizedContent = normalizeToolResultContent(content);

  // Check if tool result contains standalone file metadata
  const parsed = tryParseJSON(normalizedContent);
  if (parsed?._standalone_file) {
    const fileData = parsed._standalone_file;
    // Create a new assistant message with file content block
    const fileId = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const fileMessage: import('@/types').ChatMessage = {
      id: fileId,
      role: 'assistant',
      content: [{
        type: fileData.type as 'audio' | 'video' | 'image' | 'file',
        source: { url: fileData.url, mime_type: fileData.mime_type },
        filename: fileData.filename,
        size_bytes: fileData.size_bytes
      }],
      timestamp: new Date()
    };
    store.addMessage(fileMessage);
  }

  const message = createToolResultMessage(toolUseId, normalizedContent, isError, parentToolUseId);
  store.addMessage(message);
}

/**
 * Safely attempts to parse JSON from a string.
 * Returns null if parsing fails.
 */
function tryParseJSON(text: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(text);
    return typeof parsed === 'object' && parsed !== null ? parsed as Record<string, unknown> : null;
  } catch {
    return null;
  }
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
        contextWindow: event.usage?.context_window,
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
export function handleCompactStartedEvent(ctx: EventHandlerContext): void {
  ctx.store.setCompacting(true);
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
 * Dynamically import a store module and call an opener function.
 * Shared pattern for opening modals from WebSocket events.
 */
function openStoreModal<T>(
  importFn: () => Promise<T>,
  opener: (mod: T) => void,
  errorMsg: string,
): void {
  importFn().then(opener).catch((err) => {
    console.error(errorMsg, err);
    toast.error(errorMsg);
  });
}

/**
 * Handles the 'ask_user_question' event - agent needs user input.
 */
export function handleAskUserQuestionEvent(
  questionId: string,
  questions: RawQuestion[] | string,
  timeout: number,
): void {
  const parsedQuestions = normalizeQuestions(questions);
  if (!parsedQuestions) {
    toast.error('Invalid question format received');
    return;
  }

  const transformedQuestions = toUIQuestions(parsedQuestions);

  openStoreModal(
    () => import('@/lib/store/question-store'),
    ({ useQuestionStore }) => {
      useQuestionStore.getState().openModal(questionId, transformedQuestions, timeout);
    },
    'Failed to open question dialog',
  );
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
): void {
  const transformedSteps: UIPlanStep[] = steps.map((s) => ({
    description: s.description,
    status: (s.status as UIPlanStep['status']) || 'pending',
  }));

  openStoreModal(
    () => import('@/lib/store/plan-store'),
    ({ usePlanStore }) => {
      usePlanStore.getState().openModal(planId, title, summary, transformedSteps, timeout);
    },
    'Failed to open plan approval dialog',
  );
}

/**
 * Handles the 'file_uploaded' event.
 */
function handleFileUploadedEvent(event: FileUploadedEvent, ctx: EventHandlerContext): void {
  ctx.queryClient.invalidateQueries({ queryKey: ['files'] });
  toast.success(`File "${event.file.original_name}" uploaded`);
}

/**
 * Handles the 'file_deleted' event.
 */
function handleFileDeletedEvent(ctx: EventHandlerContext): void {
  ctx.queryClient.invalidateQueries({ queryKey: ['files'] });
  toast.success('File deleted');
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

  const safeErrorMessage = typeof errorMessage === 'string'
    ? errorMessage
    : String(errorMessage ?? 'An error occurred');

  // Handle session not found error - this is recoverable
  if (safeErrorMessage.includes('not found') && safeErrorMessage.includes('Session')) {
    console.warn('Session not found, starting fresh:', safeErrorMessage);
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
    console.error('WebSocket error:', safeErrorMessage);
    store.setConnectionStatus('error');
    toast.error(safeErrorMessage || 'An error occurred');
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
        handleAskUserQuestionEvent(
          event.question_id,
          event.questions,
          event.timeout,
        );
        break;

      case 'plan_approval':
        handlePlanApprovalEvent(
          event.plan_id,
          event.title,
          event.summary,
          event.steps,
          event.timeout,
        );
        break;

      case 'file_uploaded':
        handleFileUploadedEvent(event, ctx);
        break;

      case 'file_deleted':
        handleFileDeletedEvent(ctx);
        break;

      case 'error':
        handleErrorEvent(event.error, ctx);
        break;
    }
  };
}

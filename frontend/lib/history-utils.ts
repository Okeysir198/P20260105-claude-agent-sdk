import type { ChatMessage, ContentBlock } from '@/types';

/**
 * Raw API history message format. Uses `any` for flexibility with backend responses.
 */
interface RawHistoryMessage {
  message_id?: string;
  role: string;
  content: string | Record<string, unknown>[];
  timestamp?: string;
  tool_name?: string;
  metadata?: {
    input?: Record<string, unknown>;
    parent_tool_use_id?: string;
  };
  tool_use_id?: string;
  is_error?: boolean;
}

/** Roles that should be rendered as chat bubbles. */
const RENDERABLE_ROLES = new Set(['user', 'assistant', 'tool_use', 'tool_result']);

/**
 * Convert API history messages to ChatMessage format.
 * Handles both minimal and extended message formats from the backend.
 * Non-renderable roles (e.g. system/event) are filtered out.
 */
export function convertHistoryToChatMessages(
  messages: RawHistoryMessage[]
): ChatMessage[] {
  return messages
    .filter((msg) => RENDERABLE_ROLES.has(msg.role))
    .map((msg) => {
    // For tool_use messages, parse input from content if not in metadata
    let toolInput = msg.metadata?.input;
    if (msg.role === 'tool_use' && !toolInput && msg.content) {
      try {
        toolInput = typeof msg.content === 'string'
          ? JSON.parse(msg.content)
          : msg.content as unknown as Record<string, unknown>;
      } catch {
        // If content isn't valid JSON, leave toolInput undefined
      }
    }

    // For tool_use messages, prefer tool_use_id as the message id since
    // tool_result messages reference it via toolUseId for matching
    const id = msg.role === 'tool_use' && msg.tool_use_id
      ? msg.tool_use_id
      : msg.message_id || crypto.randomUUID();

    return {
      id,
      role: msg.role as ChatMessage['role'],
      content: (Array.isArray(msg.content) ? msg.content as unknown as ContentBlock[] : msg.content),
      timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
      toolName: msg.tool_name,
      toolInput,
      toolUseId: msg.tool_use_id,
      isError: msg.is_error,
      parentToolUseId: msg.metadata?.parent_tool_use_id,
    };
  });
}

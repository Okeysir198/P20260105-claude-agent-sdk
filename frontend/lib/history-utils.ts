import type { ChatMessage } from '@/types';

/**
 * Raw API history message format. Uses `any` for flexibility with backend responses.
 */
interface RawHistoryMessage {
  message_id?: string;
  role: string;
  content: string;
  timestamp?: string;
  tool_name?: string;
  metadata?: {
    input?: Record<string, unknown>;
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
        toolInput = JSON.parse(msg.content);
      } catch {
        // If content isn't valid JSON, leave toolInput undefined
      }
    }

    return {
      id: msg.message_id || crypto.randomUUID(),
      role: msg.role as ChatMessage['role'],
      content: msg.content,
      timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
      toolName: msg.tool_name,
      toolInput,
      toolUseId: msg.tool_use_id,
      isError: msg.is_error,
    };
  });
}

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

/**
 * Convert API history messages to ChatMessage format.
 * Handles both minimal and extended message formats from the backend.
 */
export function convertHistoryToChatMessages(
  messages: RawHistoryMessage[]
): ChatMessage[] {
  return messages.map((msg) => ({
    id: msg.message_id || crypto.randomUUID(),
    role: msg.role as ChatMessage['role'],
    content: msg.content,
    timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
    toolName: msg.tool_name,
    toolInput: msg.metadata?.input,
    toolUseId: msg.tool_use_id,
    isError: msg.is_error,
  }));
}

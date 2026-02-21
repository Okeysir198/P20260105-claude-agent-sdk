import type { ChatMessage, ContentBlock } from '@/types';
import { extractText } from '@/lib/content-utils';


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

    // Normalize array content: preserve non-text blocks (images, audio, video, files)
    // for rich rendering; only flatten to string when array is all-text
    let content: string | ContentBlock[];
    if (Array.isArray(msg.content)) {
      const blocks = msg.content as unknown as ContentBlock[];
      const hasNonTextBlocks = blocks.some(
        (b) => b && typeof b === 'object' && 'type' in b && b.type !== 'text'
      );
      if (hasNonTextBlocks) {
        // Preserve the full block array for rich media rendering
        content = blocks;
      } else if (msg.role === 'tool_result') {
        // Tool results: flatten text-only arrays to string
        content = extractText(blocks);
      } else {
        content = blocks;
      }
    } else {
      content = msg.content;
    }

    return {
      id,
      role: msg.role as ChatMessage['role'],
      content,
      timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
      toolName: msg.tool_name,
      toolInput,
      toolUseId: msg.tool_use_id,
      isError: msg.is_error,
      parentToolUseId: msg.metadata?.parent_tool_use_id,
    };
  });
}

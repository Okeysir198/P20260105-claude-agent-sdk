import type { ChatMessage, ContentBlock, AudioContentBlock, VideoContentBlock, ImageContentBlock, FileContentBlock } from '@/types';
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
 * Try to extract _standalone_file metadata from a tool_result content string.
 * Returns a ContentBlock for rendering media inline, or null if not found.
 */
function extractStandaloneFileBlock(content: string): ContentBlock | null {
  try {
    const parsed = JSON.parse(content);
    if (!parsed?._standalone_file) return null;
    const f = parsed._standalone_file as { type: string; url: string; filename?: string; mime_type?: string; size_bytes?: number };

    switch (f.type) {
      case 'audio':
        return { type: 'audio', source: { url: f.url, mime_type: f.mime_type }, filename: f.filename } as AudioContentBlock;
      case 'video':
        return { type: 'video', source: { url: f.url, mime_type: f.mime_type }, filename: f.filename } as VideoContentBlock;
      case 'image':
        return { type: 'image', source: { type: 'url' as const, url: f.url, media_type: f.mime_type } } as ImageContentBlock;
      default:
        return { type: 'file', source: { url: f.url, mime_type: f.mime_type }, filename: f.filename, size: f.size_bytes } as FileContentBlock;
    }
  } catch {
    return null;
  }
}

/**
 * Convert API history messages to ChatMessage format.
 * Handles both minimal and extended message formats from the backend.
 * Non-renderable roles (e.g. system/event) are filtered out.
 */
export function convertHistoryToChatMessages(
  messages: RawHistoryMessage[]
): ChatMessage[] {
  const result: ChatMessage[] = [];

  for (const msg of messages) {
    if (!RENDERABLE_ROLES.has(msg.role)) continue;

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

    result.push({
      id,
      role: msg.role as ChatMessage['role'],
      content,
      timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
      toolName: msg.tool_name,
      toolInput,
      toolUseId: msg.tool_use_id,
      isError: msg.is_error,
      parentToolUseId: msg.metadata?.parent_tool_use_id,
    });

    // Extract _standalone_file from tool_result to create inline media messages
    if (msg.role === 'tool_result' && typeof content === 'string') {
      const fileBlock = extractStandaloneFileBlock(content);
      if (fileBlock) {
        result.push({
          id: `file-${id}-${Date.now()}`,
          role: 'assistant',
          content: [fileBlock],
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
        });
      }
    }
  }

  return result;
}

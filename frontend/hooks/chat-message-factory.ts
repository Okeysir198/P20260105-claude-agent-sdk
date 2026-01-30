/**
 * Message factory utilities for creating ChatMessage objects.
 * Centralizes message creation logic with consistent ID generation and timestamps.
 *
 * @module chat-message-factory
 */

import type { ChatMessage, ContentBlock } from '@/types';

/**
 * Creates a user message with the given content.
 *
 * @param content - Message content (string or ContentBlock array)
 * @returns A new ChatMessage with role 'user'
 */
export function createUserMessage(content: string | ContentBlock[]): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    timestamp: new Date(),
  };
}

/**
 * Creates an assistant message with the given content.
 *
 * @param content - Message content (string or ContentBlock array)
 * @returns A new ChatMessage with role 'assistant'
 */
export function createAssistantMessage(content: string | ContentBlock[]): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content,
    timestamp: new Date(),
  };
}

/**
 * Creates a tool_use message with the given details.
 *
 * @param id - Tool use ID
 * @param name - Tool name
 * @param input - Tool input parameters
 * @returns A new ChatMessage with role 'tool_use'
 */
export function createToolUseMessage(
  id: string,
  name: string,
  input: Record<string, unknown>
): ChatMessage {
  return {
    id,
    role: 'tool_use',
    content: '',
    timestamp: new Date(),
    toolName: name,
    toolInput: input,
  };
}

/**
 * Creates a tool_result message with the given details.
 *
 * @param toolUseId - ID of the associated tool_use
 * @param content - Result content string
 * @param isError - Whether the result indicates an error
 * @returns A new ChatMessage with role 'tool_result'
 */
export function createToolResultMessage(
  toolUseId: string,
  content: string,
  isError?: boolean
): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'tool_result',
    content,
    timestamp: new Date(),
    toolUseId,
    isError,
  };
}

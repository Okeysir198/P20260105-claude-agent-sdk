import type { ChatMessage, ContentBlock } from '@/types';

/** Creates a user message with the given content. */
export function createUserMessage(content: string | ContentBlock[]): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    timestamp: new Date(),
  };
}

/** Creates an assistant message with the given content. */
export function createAssistantMessage(content: string | ContentBlock[]): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content,
    timestamp: new Date(),
  };
}

/** Creates a tool_use message for when the agent invokes a tool. */
export function createToolUseMessage(
  id: string,
  name: string,
  input: Record<string, unknown>,
  parentToolUseId?: string,
): ChatMessage {
  return {
    id,
    role: 'tool_use',
    content: '',
    timestamp: new Date(),
    toolName: name,
    toolInput: input,
    parentToolUseId,
  };
}

/** Creates a tool_result message for the output of a tool execution. */
export function createToolResultMessage(
  toolUseId: string,
  content: string,
  isError?: boolean,
  parentToolUseId?: string,
): ChatMessage {
  return {
    id: `result-${toolUseId}-${Date.now()}`,
    role: 'tool_result',
    content,
    timestamp: new Date(),
    toolUseId,
    isError: isError ?? false,
    parentToolUseId,
  };
}

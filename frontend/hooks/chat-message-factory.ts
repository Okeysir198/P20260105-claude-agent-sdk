import type { ChatMessage, ContentBlock } from '@/types';

export function createUserMessage(content: string | ContentBlock[]): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    timestamp: new Date(),
  };
}

export function createAssistantMessage(content: string | ContentBlock[]): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content,
    timestamp: new Date(),
  };
}

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

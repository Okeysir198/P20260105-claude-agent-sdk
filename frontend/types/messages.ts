/**
 * Message Types for Claude Chat UI
 * @module types/messages
 */

export interface BaseMessage {
  id: string;
  timestamp: Date;
}

export interface UserMessage extends BaseMessage {
  role: 'user';
  content: string;
}

export interface AssistantMessage extends BaseMessage {
  role: 'assistant';
  content: string;
  isStreaming?: boolean;
}

export interface ToolUseMessage extends BaseMessage {
  role: 'tool_use';
  toolName: string;
  input: Record<string, unknown>;
  toolUseId?: string;
}

export interface ToolResultMessage extends BaseMessage {
  role: 'tool_result';
  toolUseId: string;
  content: string;
  isError: boolean;
}

export interface SystemMessage extends BaseMessage {
  role: 'system';
  content: string;
  level: 'info' | 'warning' | 'error';
}

export type Message =
  | UserMessage
  | AssistantMessage
  | ToolUseMessage
  | ToolResultMessage
  | SystemMessage;

export type MessageRole = Message['role'];

export interface ConversationState {
  sessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
  turnCount: number;
  totalCostUsd?: number;
}

export const INITIAL_CONVERSATION_STATE: ConversationState = {
  sessionId: null,
  messages: [],
  isStreaming: false,
  isLoading: false,
  error: null,
  turnCount: 0,
};

// Type guards
export function isUserMessage(message: Message): message is UserMessage {
  return message.role === 'user';
}

export function isAssistantMessage(message: Message): message is AssistantMessage {
  return message.role === 'assistant';
}

export function isToolUseMessage(message: Message): message is ToolUseMessage {
  return message.role === 'tool_use';
}

export function isToolResultMessage(message: Message): message is ToolResultMessage {
  return message.role === 'tool_result';
}

export function isSystemMessage(message: Message): message is SystemMessage {
  return message.role === 'system';
}

// Factory helpers
export function createMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

export function createUserMessage(content: string): UserMessage {
  return {
    id: createMessageId(),
    role: 'user',
    content,
    timestamp: new Date(),
  };
}

export function createAssistantMessage(
  content: string = '',
  isStreaming: boolean = false
): AssistantMessage {
  return {
    id: createMessageId(),
    role: 'assistant',
    content,
    isStreaming,
    timestamp: new Date(),
  };
}

export function createToolUseMessage(
  toolName: string,
  input: Record<string, unknown>,
  toolUseId?: string
): ToolUseMessage {
  return {
    id: createMessageId(),
    role: 'tool_use',
    toolName,
    input,
    toolUseId,
    timestamp: new Date(),
  };
}

export function createToolResultMessage(
  toolUseId: string,
  content: string,
  isError: boolean = false
): ToolResultMessage {
  return {
    id: createMessageId(),
    role: 'tool_result',
    toolUseId,
    content,
    isError,
    timestamp: new Date(),
  };
}

// API types for session history
export interface HistoryMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_use?: Array<{
    id: string;
    name: string;
    input: Record<string, unknown>;
  }> | null;
  tool_results?: Array<{
    tool_use_id: string;
    content: string;
    is_error: boolean;
  }> | null;
  timestamp?: string | null;
}

export interface SessionHistoryResponse {
  session_id: string;
  messages: HistoryMessage[];
  turn_count: number;
  first_message: string | null;
}

export function convertHistoryToMessages(historyMessages: HistoryMessage[]): Message[] {
  const messages: Message[] = [];

  for (const historyMsg of historyMessages) {
    const timestamp = historyMsg.timestamp ? new Date(historyMsg.timestamp) : new Date();

    if (historyMsg.role === 'user') {
      messages.push({
        id: historyMsg.id,
        role: 'user',
        content: historyMsg.content,
        timestamp,
      });
      continue;
    }

    // Assistant message
    if (historyMsg.content) {
      messages.push({
        id: historyMsg.id,
        role: 'assistant',
        content: historyMsg.content,
        isStreaming: false,
        timestamp,
      });
    }

    // Tool use messages
    if (historyMsg.tool_use) {
      for (const tool of historyMsg.tool_use) {
        messages.push({
          id: `${historyMsg.id}-tool-${tool.id}`,
          role: 'tool_use',
          toolName: tool.name,
          input: tool.input,
          toolUseId: tool.id,
          timestamp,
        });
      }
    }

    // Tool result messages
    if (historyMsg.tool_results) {
      for (const result of historyMsg.tool_results) {
        messages.push({
          id: `${historyMsg.id}-result-${result.tool_use_id}`,
          role: 'tool_result',
          toolUseId: result.tool_use_id,
          content: result.content,
          isError: result.is_error,
          timestamp,
        });
      }
    }
  }

  return messages;
}

// types/index.ts
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// UI-transformed question types for AskUserQuestion modal
// These are transformed from WebSocket Question/QuestionOption types in use-chat.ts
export interface UIQuestionOption {
  value: string;
  description?: string;
}

export interface UIQuestion {
  question: string;
  options: UIQuestionOption[];
  allowMultiple?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool_use' | 'tool_result';
  content: string;
  timestamp: Date;
  toolName?: string;
  toolInput?: Record<string, any>;
  toolUseId?: string;
  isError?: boolean;
}

export interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
}

export interface Agent {
  agent_id: string;
  name: string;
  description: string;
  model: string;
  is_default: boolean;
}

export interface Session {
  session_id: string;
  name: string | null;
  first_message: string | null;
  created_at: string;
  turn_count: number;
  user_id: string | null;
}

// Re-export API types
export * from './api';
export * from './websocket';
